"""
JTP-3 (Hydra) inference module.

This module handles model loading, preprocessing, and inference for
JTP-3 models (NAFlex ViT + Hydra classifier head architecture).

Adapted from the JTP-3 repository for single-image GUI use.
"""

import time
from io import BytesIO
from math import ceil
from typing import Any, Callable

import torch
from torch import Tensor
from torch.nn import Module, ModuleList, Parameter, Buffer, Linear, LayerNorm, RMSNorm, Dropout, Flatten, Identity, init
from torch.nn.functional import pad, scaled_dot_product_attention, silu

import timm

import numpy as np
from einops import rearrange

from PIL import Image
from PIL.ImageCms import Direction, Intent, ImageCmsProfile, createProfile, getDefaultIntent, isIntentSupported, profileToProfile, Flags as ImageCmsFlags
from PIL.ImageOps import exif_transpose

from safetensors import safe_open


# --- Python 3.11 Compatibility ---
# itertools.batched was added in Python 3.12, we don't need it for single-image GUI


# --- GLU Activation Functions ---
class SwiGLU(Module):
    """Swish-Gated Linear Unit activation function."""

    def __init__(self, dim: int = -1) -> None:
        super().__init__()
        self.dim = dim

    def forward(self, x: Tensor) -> Tensor:
        f, g = x.chunk(2, dim=self.dim)
        return silu(f) * g


# --- Image Processing ---
Image.MAX_IMAGE_PIXELS = None  # Remove PIL's image size limit

_SRGB = createProfile(colorSpace='sRGB')

_INTENT_FLAGS = {
    Intent.PERCEPTUAL: ImageCmsFlags.HIGHRESPRECALC,
    Intent.RELATIVE_COLORIMETRIC: (
        ImageCmsFlags.HIGHRESPRECALC |
        ImageCmsFlags.BLACKPOINTCOMPENSATION
    ),
    Intent.ABSOLUTE_COLORIMETRIC: ImageCmsFlags.HIGHRESPRECALC
}


def _coalesce_intent(intent: Intent | int) -> Intent:
    """Convert integer intent to Intent enum."""
    if isinstance(intent, Intent):
        return intent

    match intent:
        case 0:
            return Intent.PERCEPTUAL
        case 1:
            return Intent.RELATIVE_COLORIMETRIC
        case 2:
            return Intent.SATURATION
        case 3:
            return Intent.ABSOLUTE_COLORIMETRIC
        case _:
            raise ValueError("invalid intent")


def process_srgb(
    img: Image.Image,
    *,
    resize: Callable[[tuple[int, int]], tuple[int, int] | None] | tuple[int, int] | None = None,
) -> Image.Image:
    """
    Process an image to sRGB color space with optional resizing.
    Handles EXIF orientation, ICC profiles, and transparency.
    """
    img.load()

    # Apply EXIF orientation
    try:
        exif_transpose(img, in_place=True)
    except Exception:
        pass  # corrupt EXIF metadata is fine

    size = (img.width, img.height)

    # Handle ICC color profile conversion to sRGB
    if (icc_raw := img.info.get("icc_profile")) is not None:
        try:
            profile = ImageCmsProfile(BytesIO(icc_raw))

            working_mode = img.mode
            if img.mode.startswith(("RGB", "BGR", "P")):
                working_mode = "RGBA" if img.has_transparency_data else "RGB"
            elif img.mode.startswith(("L", "I", "F")) or img.mode == "1":
                working_mode = "LA" if img.has_transparency_data else "L"

            if img.mode != working_mode:
                img = img.convert(working_mode)

            mode = "RGBA" if img.has_transparency_data else "RGB"

            intent = Intent.RELATIVE_COLORIMETRIC
            if isIntentSupported(profile, intent, Direction.INPUT) != 1:
                intent = _coalesce_intent(getDefaultIntent(profile))

            if (flags := _INTENT_FLAGS.get(intent)) is None:
                raise RuntimeError("Unsupported intent")

            if img.mode == mode:
                profileToProfile(
                    img,
                    profile,
                    _SRGB,
                    renderingIntent=intent,
                    inPlace=True,
                    flags=flags
                )
            else:
                img = profileToProfile(
                    img,
                    profile,
                    _SRGB,
                    renderingIntent=intent,
                    outputMode=mode,
                    flags=flags
                )
        except Exception:
            pass

    # Convert to RGB/RGBa
    if img.has_transparency_data:
        if img.mode != "RGBa":
            try:
                img = img.convert("RGBa")
            except ValueError:
                img = img.convert("RGBA").convert("RGBa")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if specified
    if resize is not None and not isinstance(resize, tuple):
        resize = resize(size)

    if resize is not None and size != resize:
        img = img.resize(
            resize,
            Image.Resampling.LANCZOS,
            reducing_gap=3.0
        )

    return img


def put_srgb_patch(
    img: Image.Image,
    patch_data: Tensor,
    patch_coord: Tensor,
    patch_valid: Tensor,
    patch_size: int
) -> None:
    """
    Extract patches from an image and store them in tensors.
    Patches are stored in row-major order with their 2D coordinates.
    """
    if img.mode not in ("RGB", "RGBA", "RGBa"):
        raise ValueError(f"Image has non-RGB mode {img.mode}.")

    # Reshape image into patches: (H/p, W/p, p*p*3)
    patches = rearrange(
        np.asarray(img)[:, :, :3],
        "(h p1) (w p2) c -> h w (p1 p2 c)",
        p1=patch_size, p2=patch_size
    )

    # Create coordinate grid
    coords = np.stack(np.meshgrid(
        np.arange(patches.shape[0], dtype=np.int16),
        np.arange(patches.shape[1], dtype=np.int16),
        indexing="ij"
    ), axis=-1)

    # Flatten
    coords = rearrange(coords, "h w c -> (h w) c")
    patches = rearrange(patches, "h w p -> (h w) p")
    n = patches.shape[0]

    # Copy to tensors
    np.copyto(patch_data[:n].numpy(), patches, casting="no")
    np.copyto(patch_coord[:n].numpy(), coords, casting="no")
    patch_valid[:n] = True


def get_image_size_for_seq(
    image_hw: tuple[int, int],
    patch_size: int = 16,
    max_seq_len: int = 1024,
    max_ratio: float = 1.0,
    eps: float = 1e-5,
) -> tuple[int, int]:
    """
    Determine optimal image size for given sequence length constraint.
    Uses binary search to find maximum resolution that fits within max_seq_len patches.
    """
    assert max_ratio >= 1.0
    assert eps * 2 < max_ratio

    h, w = image_hw
    max_py = int(max((h * max_ratio) // patch_size, 1))
    max_px = int(max((w * max_ratio) // patch_size, 1))

    if (max_py * max_px) <= max_seq_len:
        return max_py * patch_size, max_px * patch_size

    def patchify(ratio: float) -> tuple[int, int]:
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


# --- Hydra Pool Classifier Head ---
class IndexedAdd(Module):
    """Indexed addition operation for Hydra roots."""

    def __init__(
        self,
        n_indices: int,
        dim: int,
        weight_shape: tuple[int, ...] | None = None,
        *,
        inplace: bool = False,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.dim = dim
        self.inplace = inplace

        self.index = Buffer(torch.empty(
            2, n_indices,
            device=device, dtype=torch.int32
        ))

        self.weight = Parameter(torch.ones(
            *(sz if sz != -1 else n_indices for sz in weight_shape),
            device=device, dtype=dtype
        )) if weight_shape is not None else None

    def forward(self, dst: Tensor, src: Tensor) -> Tensor:
        src = src.index_select(self.dim, self.index[0])

        if self.weight is not None:
            src.mul_(self.weight)

        return (
            dst.index_add_(self.dim, self.index[1], src)
            if self.inplace else
            dst.index_add(self.dim, self.index[1], src)
        )


class BatchLinear(Module):
    """Batched linear layer for per-class transformations."""

    def __init__(
        self,
        batch_shape: tuple[int, ...] | int,
        in_features: int,
        out_features: int,
        *,
        bias: bool = False,
        flatten: bool = False,
        bias_inplace: bool = True,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        if isinstance(batch_shape, int):
            batch_shape = (batch_shape,)
        elif not batch_shape:
            raise ValueError("At least one batch dimension is required.")

        self.flatten = -(len(batch_shape) + 1) if flatten else 0

        self.weight = Parameter(torch.empty(
            *batch_shape, in_features, out_features,
            device=device, dtype=dtype
        ))

        bt = self.weight.flatten(end_dim=-3).mT
        for idx in range(bt.size(0)):
            init.kaiming_uniform_(bt[idx], a=np.sqrt(5))

        self.bias = Parameter(torch.zeros(
            *batch_shape, out_features,
            device=device, dtype=dtype
        )) if bias else None

        self.bias_inplace = bias_inplace

    def forward(self, x: Tensor) -> Tensor:
        # ... B... 1 I @ B... I O -> ... B... O
        x = torch.matmul(x.unsqueeze(-2), self.weight).squeeze(-2)

        if self.bias is not None:
            if self.bias_inplace:
                x.add_(self.bias)
            else:
                x = x + self.bias

        if self.flatten:
            x = x.flatten(self.flatten)

        return x


class Mean(Module):
    """Mean pooling module."""

    def __init__(self, dim: tuple[int, ...] | int = -1, *, keepdim: bool = False) -> None:
        super().__init__()
        self.dim = dim
        self.keepdim = keepdim

    def forward(self, x: Tensor) -> Tensor:
        return x.mean(self.dim, self.keepdim)


class HydraPool(Module):
    """
    Hydra classifier head with per-tag attention queries.
    Each tag learns its own query vector to attend over image patches.
    """

    def __init__(
        self,
        attn_dim: int,
        head_dim: int,
        n_classes: int,
        *,
        mid_blocks: int = 0,
        roots: tuple[int, int, int] = (0, 0, 0),
        ff_ratio: float = 3.0,
        ff_dropout: float = 0.0,
        input_dim: int = -1,
        output_dim: int = 1,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        if input_dim < 0:
            input_dim = attn_dim

        assert attn_dim % head_dim == 0
        n_heads = attn_dim // head_dim

        self.n_classes = n_classes
        self.head_dim = head_dim
        self.output_dim = output_dim

        self._has_roots = False
        self._has_ff = False

        self.q: Parameter | Buffer
        self._q_normed: bool | None

        # Handle roots (hierarchical tag structure)
        if roots != (0, 0, 0):
            self._has_roots = True
            n_roots, n_classroots, n_subclasses = roots

            if n_classroots < n_roots:
                raise ValueError("Number of classroots cannot be less than the number of roots.")

            self.cls = Parameter(torch.randn(
                n_heads, n_classes, head_dim,
                device=device, dtype=dtype
            ))

            self.roots = Parameter(torch.randn(
                n_heads, n_roots, head_dim,
                device=device, dtype=dtype
            )) if n_roots > 0 else None

            self.clsroots = IndexedAdd(
                n_classroots, dim=-2, weight_shape=(n_heads, -1, 1),
                device=device, dtype=dtype
            ) if n_classroots > 0 else None

            self.clscls = IndexedAdd(
                n_subclasses, dim=-2, weight_shape=(n_heads, -1, 1),
                inplace=True, device=device, dtype=dtype
            ) if n_subclasses > 0 else None

            self.q = Buffer(torch.empty(
                n_heads, n_classes, head_dim,
                device=device, dtype=dtype
            ))
            self._q_normed = None
        else:
            self.q = Parameter(torch.randn(
                n_heads, n_classes, head_dim,
                device=device, dtype=dtype
            ))
            self._q_normed = False

        # Key-value projection
        self.kv = Linear(
            input_dim, attn_dim * 2, bias=False,
            device=device, dtype=dtype
        )
        self.qk_norm = RMSNorm(
            head_dim, eps=1e-5, elementwise_affine=False
        )

        # Feedforward layers
        if ff_ratio > 0.0:
            self._has_ff = True
            hidden_dim = int(attn_dim * ff_ratio)

            self.ff_norm = LayerNorm(
                attn_dim,
                device=device, dtype=dtype
            )
            self.ff_in = Linear(
                attn_dim, hidden_dim * 2, bias=False,
                device=device, dtype=dtype
            )
            self.ff_act = SwiGLU()
            self.ff_drop = Dropout(ff_dropout)
            self.ff_out = Linear(
                hidden_dim, attn_dim, bias=False,
                device=device, dtype=dtype
            )
        elif mid_blocks > 0:
            raise ValueError("Feedforward required with mid blocks.")

        self.mid_blocks = ModuleList()  # Mid blocks not implemented for simplicity

        # Output projection
        self.out_proj = BatchLinear(
            n_classes, attn_dim, output_dim * 2,
            device=device, dtype=dtype
        )
        self.out_act = SwiGLU()

    def get_extra_state(self) -> dict[str, Any]:
        return {"q_normed": self._q_normed}

    def set_extra_state(self, state: dict[str, Any]) -> None:
        self._q_normed = state["q_normed"]

    def create_head(self) -> Module:
        if self.output_dim == 1:
            return Flatten(-2)
        return Mean(-1)

    def _cache_query(self) -> None:
        """Pre-compute and cache normalized queries for inference."""
        assert not self.training

        if self._q_normed:
            return

        with torch.no_grad():
            self.q.to(device=self.kv.weight.device)
            self.q.copy_(self._forward_q())
            self._q_normed = True

    def _forward_q(self) -> Tensor:
        """Compute query vectors (with optional root composition)."""
        match self._q_normed:
            case None:
                assert self._has_roots

                if self.roots is not None:
                    q = self.qk_norm(self.roots)
                    q = self.clsroots(self.cls, q)
                else:
                    q = self.cls

                if self.clscls is not None:
                    q = self.clscls(q, q.detach())

                q = self.qk_norm(q)
                return q

            case False:
                assert not self._has_roots
                return self.qk_norm(self.q)

            case True:
                return self.q

    def _forward_attn(self, x: Tensor, attn_mask: Tensor | None) -> tuple[Tensor, Tensor, Tensor]:
        """Compute cross-attention between queries and image patches."""
        q = self._forward_q().expand(*x.shape[:-2], -1, -1, -1)

        x = self.kv(x)
        k, v = rearrange(x, "... s (n h e) -> n ... h s e", n=2, e=self.head_dim).unbind(0)
        k = self.qk_norm(k)

        x = scaled_dot_product_attention(q, k, v, attn_mask=attn_mask)
        return rearrange(x, "... h s e -> ... s (h e)"), k, v

    def _forward_ff(self, x: Tensor) -> Tensor:
        """Apply feedforward layers."""
        if not self._has_ff:
            return x

        f = self.ff_norm(x)
        f = self.ff_in(f)
        f = self.ff_act(f)
        f = self.ff_drop(f)
        f = self.ff_out(f)
        return x + f

    def _forward_out(self, x: Tensor) -> Tensor:
        """Apply output projection."""
        x = self.out_proj(x)
        x = self.out_act(x)
        return x

    def forward(self, x: Tensor, attn_mask: Tensor | None = None) -> Tensor:
        x, k, v = self._forward_attn(x, attn_mask)
        x = self._forward_ff(x)
        # Mid blocks skipped for simplicity
        x = self._forward_out(x)
        return x

    @staticmethod
    def for_state(
        state_dict: dict[str, Any],
        prefix: str = "",
        *,
        ff_dropout: float = 0.0,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> "HydraPool":
        """Create HydraPool from state dict metadata."""
        n_heads, n_classes, head_dim = state_dict[f"{prefix}q"].shape
        attn_dim = n_heads * head_dim

        roots_t = state_dict.get(f"{prefix}roots")
        clsroots_t = state_dict.get(f"{prefix}clsroots.index")
        clscls_t = state_dict.get(f"{prefix}clscls.index")
        roots = (
            roots_t.size(1) if roots_t is not None else 0,
            clsroots_t.size(1) if clsroots_t is not None else 0,
            clscls_t.size(1) if clscls_t is not None else 0
        )

        input_dim = state_dict[f"{prefix}kv.weight"].size(1)
        output_dim = state_dict[f"{prefix}out_proj.weight"].size(2) // 2

        # Infer ff_ratio from hidden_dim
        ffout_t = state_dict.get(f"{prefix}ff_out.weight")
        hidden_dim = ffout_t.size(1) + 0.5 if ffout_t is not None else 0
        ff_ratio = hidden_dim / attn_dim

        return HydraPool(
            attn_dim,
            head_dim,
            n_classes,
            mid_blocks=0,  # Simplified: no mid blocks
            roots=roots,
            ff_ratio=ff_ratio,
            ff_dropout=ff_dropout,
            input_dim=input_dim,
            output_dim=output_dim,
            device=device,
            dtype=dtype
        )


# --- Attention Mask for NAFlex ---
def sdpa_attn_mask(
    patch_valid: Tensor,
    num_prefix_tokens: int = 0,
    symmetric: bool = True,
    q_len: int | None = None,
    dtype: torch.dtype | None = None,
) -> Tensor:
    """Create attention mask from patch validity tensor for JTP-3."""
    mask = patch_valid.unflatten(-1, (1, 1, -1))

    if num_prefix_tokens:
        mask = torch.cat((
            torch.ones(
                *mask.shape[:-1], num_prefix_tokens,
                device=patch_valid.device, dtype=torch.bool
            ), mask
        ), dim=-1)

    return mask


# Patch timm's NAFlex attention mask function for JTP-3 compatibility
timm.models.naflexvit.create_attention_mask = sdpa_attn_mask


# --- Model Loading ---
def load_jtp3_model(
    model_path: str,
    device: torch.device
) -> tuple[torch.nn.Module, list[str]]:
    """
    Load a JTP-3 model from a safetensors file.

    Args:
        model_path: Path to the .safetensors model file
        device: Torch device to load the model onto

    Returns:
        Tuple of (model, list of tag names)
    """
    load_start_time = time.time()
    print(f"LoadJTP3: Loading model from {model_path}...")

    # Load model metadata and weights
    with safe_open(model_path, framework="pt", device="cpu") as file:
        metadata = file.metadata()
        state_dict = {
            key: file.get_tensor(key)
            for key in file.keys()
        }

    # Check architecture
    arch = metadata["modelspec.architecture"]
    if not arch.startswith("naflexvit_so400m_patch16_siglip"):
        raise ValueError(f"Unrecognized model architecture: {arch}")

    # Extract tags from metadata
    tags = metadata["classifier.labels"].split("\n")
    print(f"LoadJTP3: Loaded {len(tags)} tags from model metadata.")

    # Create base model
    print("LoadJTP3: Creating NAFlex ViT model structure...")
    model = timm.create_model(
        'naflexvit_so400m_patch16_siglip',
        pretrained=False, num_classes=0,
        pos_embed_interp_mode="bilinear",
        weight_init="skip", fix_init=False,
        device="cpu", dtype=torch.bfloat16,
    )

    # Handle different head architectures
    arch_suffix = arch[31:]  # Extract suffix after "naflexvit_so400m_patch16_siglip"

    if arch_suffix == "+rr_hydra":
        print("LoadJTP3: Using Hydra classifier head...")
        model.attn_pool = HydraPool.for_state(
            state_dict, "attn_pool.",
            device=device, dtype=torch.bfloat16
        )
        model.head = model.attn_pool.create_head()
        model.num_classes = len(tags)
        state_dict["attn_pool._extra_state"] = {"q_normed": True}
    else:
        raise ValueError(f"Unsupported JTP-3 architecture suffix: {arch_suffix}")

    # Load weights
    print("LoadJTP3: Loading model weights...")
    model.eval().to(dtype=torch.bfloat16)
    model.load_state_dict(state_dict, strict=True)
    model.to(device=device)

    # Cache queries for inference
    model.attn_pool._cache_query()

    load_end_time = time.time()
    print(f"LoadJTP3: Model loaded in {load_end_time - load_start_time:.2f} seconds.")

    return model, tags


# --- Preprocessing ---
def preprocess_jtp3(
    image_path: str,
    patch_size: int = 16,
    max_seqlen: int = 1024
) -> tuple[Tensor, Tensor, Tensor]:
    """
    Preprocess an image for JTP-3 inference.

    Args:
        image_path: Path to the image file
        patch_size: Size of each patch (default: 16)
        max_seqlen: Maximum number of patches (default: 1024)

    Returns:
        Tuple of (patches, patch_coords, patch_valid)
        - patches: Tensor of shape (max_seqlen, patch_size*patch_size*3)
        - patch_coords: Tensor of shape (max_seqlen, 2) with (y, x) coordinates
        - patch_valid: Boolean tensor of shape (max_seqlen) indicating valid patches
    """
    print(f"PreprocessJTP3: Loading and processing image {image_path}...")

    # Load and process image
    with open(image_path, "rb", buffering=(1024 * 1024)) as file:
        img: Image.Image = Image.open(file)

        try:
            # Determine optimal resize dimensions
            def compute_resize(wh: tuple[int, int]) -> tuple[int, int]:
                h, w = get_image_size_for_seq((wh[1], wh[0]), patch_size, max_seqlen)
                return w, h

            processed = process_srgb(img, resize=compute_resize)
        except:
            img.close()
            raise

    if img is not processed:
        img.close()

    print(f"PreprocessJTP3: Resized to {processed.size}, patchifying...")

    # Create patch tensors
    patches = torch.zeros(max_seqlen, patch_size * patch_size * 3, device="cpu", dtype=torch.uint8)
    patch_coords = torch.zeros(max_seqlen, 2, device="cpu", dtype=torch.int16)
    patch_valid = torch.zeros(max_seqlen, device="cpu", dtype=torch.bool)

    # Extract patches
    put_srgb_patch(processed, patches, patch_coords, patch_valid, patch_size)

    print(f"PreprocessJTP3: Extracted {patch_valid.sum().item()} patches.")

    return patches, patch_coords, patch_valid


# --- Inference ---
def run_inference_jtp3(
    model: torch.nn.Module,
    patches: Tensor,
    coords: Tensor,
    valid: Tensor,
    device: torch.device
) -> Tensor:
    """
    Run inference with a JTP-3 model.

    Args:
        model: The loaded model
        patches: Patch data tensor (shape: [max_seqlen, patch_size^2*3])
        coords: Patch coordinates tensor (shape: [max_seqlen, 2])
        valid: Patch validity mask (shape: [max_seqlen])
        device: Torch device

    Returns:
        Tensor of confidence scores for each tag (shape: [num_classes])
        Values range from -1.0 (absent) to 1.0 (present), with 0.0 being neutral
    """
    print("InferenceJTP3: Running inference...")
    start_inference = time.time()

    # Move to device and prepare tensors
    patches = patches.unsqueeze(0).to(device=device, non_blocking=True)
    coords = coords.unsqueeze(0).to(device=device, non_blocking=True)
    valid = valid.unsqueeze(0).to(device=device, non_blocking=True)

    # Normalize patches: uint8 [0, 255] -> bfloat16 [-1, 1]
    patches = patches.to(dtype=torch.bfloat16).div_(127.5).sub_(1.0)
    coords = coords.to(dtype=torch.int32)

    # Run inference
    with torch.no_grad():
        logits = model(patches, coords, valid)

    # Convert logits to probabilities and rescale to -1..1 range
    probabilities = logits.float().sigmoid()[0]  # Remove batch dim
    probabilities = (probabilities * 2.0) - 1.0  # Scale to -1..1 (1=present, 0=neutral, -1=absent)

    end_inference = time.time()
    print(f"InferenceJTP3: Inference took {end_inference - start_inference:.3f} seconds.")

    return probabilities
