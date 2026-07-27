import csv
import os

from collections import defaultdict
from itertools import islice
from math import ceil
from typing import Generic, TypeVar, Iterable, Any

from ._compat import Self

import torch
from torch import Tensor
from torch.nn import Module

from safetensors import safe_open

from .image import (
    Color, Image, Kernel, Source, Size,
    open_srgb, put, put_patches, as_tensor,
)
from .siglip2 import NaFlexVit, NaFlexFeatures, NaFlexFeaturesVarlen
from .pool import HydraPool
from .head import LinearHead, SwiGLUHead, ExtremumPool

from .classification import Calibration, MetricLike, DEFAULT_METRIC
from .label import Label, TAG_CATEGORIES

__all__ = (
    "Hydra", "Extension", "ImageConfig",
    "open_image", "load_image", "get_image_size_for_seq",
    "load_model",
)

P = TypeVar("P", bound=Module, covariant=True)
H = TypeVar("H", bound=Module, covariant=True)
E = TypeVar("E", bound=Module, covariant=True)

class ImageConfig:
    def __init__(self, metadata: dict[str, str]) -> None:
        self.background: Color
        match metadata.get("classifier.background", "black"):
            case "black":
                self.background = 0
            case "grey":
                self.background = 127
            case "white":
                self.background = 255
            case _:
                raise ValueError("Unrecognized classifier.background metadata.")

        match metadata.get("classifier.resize", "lanczos"):
            case "lanczos":
                self.resize_kernel = Kernel.LANCZOS3
                self.resize_linear = False
            case "mks2013-linear":
                self.resize_kernel = Kernel.MKS2013
                self.resize_linear = True
            case _:
                raise ValueError("Unrecognized classifier.resize metadata.")

        self.patch_size = 16
        self.max_seqlen = 1024

class Extension:
    path: str
    model: str
    architecture: str
    label: Label
    parameters: dict[str, Tensor]

    def __init__(self) -> None:
        self.path = ""
        self.model = ""
        self.parameters = {}

    @classmethod
    def load(cls, path: str, *, metadata_only: bool = False) -> Self:
        ext = cls()

        with safe_open(path, framework="pt", device="cpu") as file:
            metadata = file.metadata()

            impl = metadata.get("modelspec.implementation")
            match impl:
                case None:
                    raise RuntimeError(f"File {repr(path)} is missing SAI modelspec metadata.")

                case "redrocket.extension.label.v1":
                    ext.model = "JTP-3 beta6-pruned"

                    if not metadata_only:
                        ext.parameters = {
                            "attn_pool.q": file.get_tensor("q"),
                            "head.proj.weight": file.get_tensor("out_proj.weight"),
                        }

                case "redrocket.extension.label.v2":
                    ext.model = metadata["classifier.model"]

                    if not metadata_only:
                        ext.parameters = {
                            key: file.get_tensor(key)
                            for key in file.keys()
                            if key != "validation"
                        }

                case _:
                    raise RuntimeError(f"File {repr(path)} has unrecognized implementation {repr(impl)}.")

            validation = file.get_tensor("validation")

        ext.path = path
        ext.architecture = metadata["modelspec.architecture"]
        ext.label = Label(
            metadata["classifier.label"],
            metadata.get("classifier.label.category", "general"),
            metadata.get("classifier.label.implies", "").split(),
            validation,
            implied_by=metadata.get("classifier.label.impliedby", "").split(),
        )

        return ext

    @classmethod
    def discover(cls, paths: Iterable[str] | str) -> Iterable[str]:
        if isinstance(paths, str):
            paths = (paths,)

        for path in paths:
            if os.path.isdir(path):
                for entry in os.scandir(path):
                    if (
                        entry.is_file()
                        and entry.name.endswith(".safetensors")
                        and not entry.name.startswith(".")
                    ):
                        yield entry.path
            else:
                yield path

class Hydra(NaFlexVit, Generic[P, H, E]):
    attn_pool: P
    head: H
    emb_head: E

    name: str
    architecture: str
    labels: list[Label]
    image_config: ImageConfig
    graph_initialized: bool

    @property
    def num_classes(self):
        return self.attn_pool.n_classes

    @torch.no_grad()
    def load_extensions(
        self, extensions: Iterable[Extension | str], *,
        strict: bool = True,
        metadata_only: bool = False,
    ) -> list[Extension]:
        loaded: list[Extension] = []
        indices = {
            label.label: idx
            for idx, label in enumerate(self.labels)
        }

        append: dict[str, list[Tensor]] = defaultdict(list)
        for ext in extensions:
            if isinstance(ext, str):
                try:
                    ext = Extension.load(ext, metadata_only=metadata_only)
                except:
                    if not strict:
                        continue

                    raise

            if ext.model not in (self.name, ""):
                if strict:
                    raise RuntimeError(f"Extension {repr(ext.path or ext.label.label)} is for model {repr(ext.model)}, not {repr(self.name)}.")

                continue

            ext_idx = indices.get(ext.label.label, -1)
            if ext_idx == -2:
                raise RuntimeError(f"Extension {repr(ext.path or ext.label.label)} conflicts with an earlier extension.")

            loaded.append(ext)

            if ext_idx == -1:
                indices[ext.label.label] = -2
                self.labels.append(ext.label)

            for name, data in ext.parameters.items():
                target = self.get_parameter(name)

                if ext_idx == -1:
                    append[name].append(data.to(device=target.device, non_blocking=True))
                else:
                    clsdim = getattr(target, "rr_clsdim")
                    target.select(clsdim, ext_idx).copy_(data.squeeze(clsdim), non_blocking=True)

        for name, tensors in append.items():
            target = self.get_parameter(name)
            target.data = torch.cat([target, *tensors], dim=getattr(target, "rr_clsdim"))

        if loaded and getattr(self, "graph_initialized", False):
            self.graph_initialized = False

        return loaded

    @torch.no_grad()
    def select_indices(self, indices: Iterable[int] | int | None, *, save: bool=True) -> None:
        if isinstance(indices, int):
            indices = (indices,)

        indices = torch.tensor(list(indices), dtype=torch.int32) if indices is not None else None

        for tensor in self.parameters():
            if (clsdim := getattr(tensor, "rr_clsdim", None)) is None:
                continue

            match data := getattr(tensor, "rr_clssaved", None):
                case False:
                    raise RuntimeError("Class data was not saved.")

                case None:
                    if indices is None:
                        continue

                    if save:
                        setattr(tensor, "rr_clssaved", tensor.data)

                    data = tensor.data

            if indices is None:
                tensor.data = data
                delattr(tensor, "rr_clssaved")
            else:
                indices = indices.to(device=data.device)
                tensor.data = data.index_select(clsdim, indices)

                if not save:
                    setattr(tensor, "rr_clssaved", False)

    def select_labels(self, labels: Iterable[str] | str | None, *, save: bool=True) -> None:
        if labels is None:
            self.select_indices(None, save=save)
            return

        if isinstance(labels, (set, frozenset)):
            label_set = labels
        elif isinstance(labels, str):
            label_set = frozenset((labels,))
        else:
            label_set = frozenset(labels)

        self.select_indices((
            idx
            for idx, label in enumerate(self.labels)
            if label.label in label_set
        ), save=save)

    def calibrate(self, metric: MetricLike = DEFAULT_METRIC) -> Calibration:
        self.ensure_label_graph()
        return Calibration(self.labels, metric)

    def open_image(self, img: Source, max_seqlen: int | None = None) -> Image:
        return open_image(img, self.image_config, max_seqlen)

    def load_image(self, img: Source, max_seqlen: int | None = None) -> Tensor:
        return load_image(img, self.image_config, max_seqlen)

    def get_categories(self) -> set[str]:
        categories: set[str] = set()

        for label in self.labels:
            categories.add(label.category)
            if (subcategory := label.subcategory) is not None:
                categories.add(subcategory)

        return categories

    def label_names(self) -> Iterable[str]:
        for label in self.labels:
            yield label.label

    def ensure_label_graph(self) -> dict[str, Label] | None:
        match getattr(self, "graph_initialized", None):
            case False:
                for label in self.labels:
                    label.implied_by.clear()
            case True:
                return None

        self.graph_initialized = False
        graph = Label.init_graph(self.labels)
        self.graph_initialized = True

        return graph

def get_image_size_for_seq(
    image_size: Size,
    patch_size: int = 16,
    max_seq_len: int = 1024,
    max_ratio: float = 1.0,
    eps: float = 1e-5,
) -> Size:
    assert max_ratio >= 1.0
    assert eps * 2.0 < max_ratio

    h, w = image_size
    max_py = int(max((h * max_ratio) // patch_size, 1))
    max_px = int(max((w * max_ratio) // patch_size, 1))

    if (max_py * max_px) <= max_seq_len:
        return max_py * patch_size, max_px * patch_size

    def patchify(ratio: float) -> Size:
        return (
            min(int(ceil((h * ratio) / patch_size)), max_py),
            min(int(ceil((w * ratio) / patch_size)), max_px)
        )

    py, px = patchify(eps)
    if (py * px) > max_seq_len:
        raise ValueError(f"Image of size {w}x{h} is too large.")

    ratio = eps
    while (max_ratio - ratio) >= eps:
        mid = (ratio + max_ratio) / 2.0

        mpy, mpx = patchify(mid)
        seq_len = mpy * mpx

        if seq_len > max_seq_len:
            max_ratio = mid
            continue

        ratio = mid
        py = mpy
        px = mpx

        if seq_len == max_seq_len:
            break

    assert py >= 1 and px >= 1
    return py * patch_size, px * patch_size

def open_image(img: Source, config: ImageConfig, max_seqlen: int | None = None) -> Image:
    if max_seqlen is None:
        max_seqlen = config.max_seqlen

    def compute_resize(size: Size) -> Size:
        return get_image_size_for_seq(size, config.patch_size, max_seqlen)

    return open_srgb(
        img,
        resize=compute_resize,
        background=config.background,
        kernel=config.resize_kernel,
        linear=config.resize_linear,
    )

def load_image(img: Source, config: ImageConfig, max_seqlen: int | None = None) -> Tensor:
    return as_tensor(open_image(img, config, max_seqlen))

def load_model(
    path: str,
    *,
    metadata_only: bool = False,
    logit: bool = False,
    ff_dropout: float = 0.0,
    reset_labels: list[Label] | None = None,
    legacy_metadata_dir: str | None = None,
) -> Hydra[Module, Module, Module]:
    state_dict: dict[str, Any] = {}
    with safe_open(path, framework="pt", device="cpu") as file:
        metadata = file.metadata()

        for key in file.keys():
            if not metadata_only or key == "validation":
                state_dict[key] = file.get_tensor(key)

    name = metadata["modelspec.title"]
    arch = metadata["modelspec.architecture"]

    model: Hydra[Module, Module, Module]
    match arch:
        case "naflexvit_so400m_patch16_siglip+rr_hydra":
            model = Hydra[HydraPool, SwiGLUHead, ExtremumPool](device="cpu", dtype=torch.bfloat16)

            if not metadata_only:
                state_dict["attn_pool.ff.proj_in.weight"] = state_dict.pop("attn_pool.ff_in.weight")
                state_dict["attn_pool.ff.proj_out.weight"] = state_dict.pop("attn_pool.ff_out.weight")
                state_dict["attn_pool.ff.norm.weight"] = state_dict.pop("attn_pool.ff_norm.weight")
                state_dict["attn_pool.ff.norm.bias"] = state_dict.pop("attn_pool.ff_norm.bias")
                state_dict["head.proj.weight"] = state_dict.pop("attn_pool.out_proj.weight").mT

            if reset_labels is None:
                if legacy_metadata_dir is None:
                    raise ValueError("Metadata directory required for rr_hydra.")

                prefix = os.path.join(
                    legacy_metadata_dir,
                    os.path.splitext(os.path.basename(path))[0]
                )

                meta = load_metadata_csv(f"{prefix}-tags.csv")
                val = load_validation_csv(f"{prefix}-val.csv")
                model.labels = [
                    Label(label, *meta[label], val[label])
                    for label in metadata["classifier.labels"].split()
                ]
            else:
                model.labels = reset_labels

            model.attn_pool = HydraPool(
                len(model.labels), 2048, 64,
                input_dim=1152, mid_blocks=0,
                ff_dim=6144, ff_dropout=ff_dropout,
                device="cpu", dtype=torch.bfloat16
            )

            model.head = SwiGLUHead(
                len(model.labels), 2048, logit=logit,
                device="cpu", dtype=torch.bfloat16
            )

            model.emb_head = ExtremumPool()

        case "naflexvit_so400m_patch16_siglip+rr_hydra2":
            model = Hydra[HydraPool, LinearHead, ExtremumPool](device="cpu", dtype=torch.bfloat16)

            validation = state_dict.pop("validation")

            if reset_labels is None:
                model.labels = []
                for idx, row in enumerate(metadata["classifier.labels"].split("\n")):
                    fields = row.split(" ")
                    model.labels.append(Label(
                        fields[0], fields[1],
                        islice(fields, 2, None),
                        validation[idx]
                    ))
            else:
                model.labels = reset_labels

            model.attn_pool = HydraPool(
                len(model.labels), 2048, 64,
                input_dim=1152, mid_blocks=1,
                ff_dim=5120, ff_dropout=ff_dropout,
                device="cpu", dtype=torch.bfloat16
            )

            model.head = LinearHead(
                len(model.labels), 2048, logit=logit,
                device="cpu", dtype=torch.bfloat16
            )

            model.emb_head = ExtremumPool()
        case _:
            raise ValueError(f"Unrecognized model architecture: {arch}")

    model.name = name
    model.architecture = arch
    model.image_config = ImageConfig(metadata)

    if not metadata_only:
        if reset_labels is not None:
            for name, tensor in model.named_parameters():
                if hasattr(tensor, "rr_clsdim"):
                    del state_dict[name]

            model.load_state_dict(state_dict, strict=False)
        else:
            model.load_state_dict(state_dict, strict=True)

    model.eval()
    model.requires_grad_(False)
    return model

# Legacy JTP-3 external metadata support.

def load_metadata_csv(path: str) -> dict[str, tuple[str, list[str]]]:
    with open(path, "r", encoding="utf-8", newline="") as file:
        return parse_metadata_csv(file)

def parse_metadata_csv(io) -> dict[str, tuple[str, list[str]]]:
    reader = csv.DictReader(io)
    if (
        reader.fieldnames is None
        or "tag" not in reader.fieldnames
        or "category" not in reader.fieldnames
        or "implications" not in reader.fieldnames
    ):
        raise RuntimeError("CSV must have the columns 'tag', 'category', and 'implications'.")

    return {
        row["tag"]: (
            TAG_CATEGORIES[int(row["category"])],
            row["implications"].split()
        )
        for row in reader
    }

def load_validation_csv(path: str) -> dict[str, Tensor]:
    with open(path, "r", encoding="utf-8", newline="") as file:
        return parse_validation_csv(file)

def parse_validation_csv(io) -> dict[str, Tensor]:
    reader = csv.DictReader(io)
    if (
        reader.fieldnames is None
        or "tag" not in reader.fieldnames
        or "threshold" not in reader.fieldnames
        or "tp" not in reader.fieldnames
        or "fp" not in reader.fieldnames
        or "tn" not in reader.fieldnames
        or "fn" not in reader.fieldnames
    ):
        raise RuntimeError("CSV must have the columns 'tag', 'threshold', 'tp', 'fp', 'tn', and 'fn'.")

    validation: dict[str, list[tuple[float, list[float]]]] = defaultdict(list)
    for row in reader:
        validation[row["tag"]].append((
            float(row["threshold"]),
            [float(row["tp"]), float(row["fp"]), float(row["tn"]), float(row["fn"])]
        ))

    tensors: dict[str, Tensor] = {}
    for label, rows in validation.items():
        rows.sort(key=lambda item: item[0])
        tensors[label] = torch.tensor(
            [counts for _, counts in rows],
            device="cpu", dtype=torch.float32
        )

    return tensors
