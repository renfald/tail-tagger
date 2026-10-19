"""
Hydra inference wrappers (JTP-3 Hydra and Hydra 3.5).

Thin adapters over the vendored ``tail_tagger.hydra`` package (RedRocket's Hydra
release). These cover both:

- **JTP-3 Hydra** (architecture ``naflexvit_so400m_patch16_siglip+rr_hydra``),
  which requires external ``<name>-tags.csv`` / ``<name>-val.csv`` metadata via
  ``legacy_metadata_dir``.
- **Hydra 3.5** (``naflexvit_so400m_patch16_siglip+rr_hydra2``), self-contained
  (labels + validation embedded in the ``.safetensors``).

Only load / preprocess / raw-forward live here. Postprocessing (per-tag
calibration, implications, thresholding) is owned by the caller
(``ClassifierManager``) through ``model.calibrate(...)`` and
``Calibration.classify_output(...)``, because it depends on live UI state
(the confidence slider and implication mode) and is cached/re-run without
re-running the model.
"""

import os
import time

import torch
from torch import Tensor

from tail_tagger.hydra import image, load_model
from tail_tagger.hydra.model import Hydra


class HydraMetadataMissingError(FileNotFoundError):
    """
    Raised when a legacy Hydra model (JTP-3, ``rr_hydra``) is loaded without its
    external ``<name>-tags.csv`` / ``<name>-val.csv`` metadata.

    Carries a user-facing, actionable message (which files, where, and where the
    download instructions live) so the UI can surface it directly instead of a
    raw ``[Errno 2]`` path.
    """


def load_hydra_model(
    model_path: str,
    device: torch.device,
    legacy_metadata_dir: str | None = None,
) -> tuple[Hydra, list[str]]:
    """
    Load a Hydra model (JTP-3 or 3.5) from a safetensors file.

    Args:
        model_path: Path to the ``.safetensors`` model file.
        device: Torch device to place the model on.
        legacy_metadata_dir: Directory containing ``<name>-tags.csv`` and
            ``<name>-val.csv``. Required for the legacy ``+rr_hydra`` (JTP-3)
            architecture; ignored for ``+rr_hydra2`` (Hydra 3.5).

    Returns:
        Tuple of (model, list of tag names in output order).
    """
    load_start_time = time.time()
    print(f"LoadHydra: Loading model from {model_path}...")

    try:
        model = load_model(model_path, legacy_metadata_dir=legacy_metadata_dir)
    except FileNotFoundError as e:
        # A legacy rr_hydra model (JTP-3) reads <name>-tags.csv / <name>-val.csv
        # from legacy_metadata_dir. If those are absent, load_model raises a bare
        # FileNotFoundError with a cryptic errno path. Translate it into an
        # actionable message. (Hydra 3.5 / rr_hydra2 never opens these, so this
        # only ever triggers for a legacy model missing its metadata.)
        missing = os.path.basename(getattr(e, "filename", "") or "")
        if legacy_metadata_dir and missing.endswith(("-tags.csv", "-val.csv")):
            prefix = os.path.splitext(os.path.basename(model_path))[0]
            tags_name = f"{prefix}-tags.csv"
            val_name = f"{prefix}-val.csv"
            folder = os.path.basename(os.path.normpath(legacy_metadata_dir)) or legacy_metadata_dir
            raise HydraMetadataMissingError(
                f"The '{folder}' model is missing its metadata files. "
                f"Place '{tags_name}' and '{val_name}' in '{legacy_metadata_dir}' "
                f"— see DOWNLOAD_INSTRUCTIONS.md in that folder."
            ) from e
        raise
    model.to(device=device)

    labels = list(model.label_names())
    print(
        f"LoadHydra: Loaded '{model.name}' ({model.architecture}) "
        f"with {len(labels)} tags."
    )

    load_end_time = time.time()
    print(f"LoadHydra: Model loaded in {load_end_time - load_start_time:.2f} seconds.")

    return model, labels


def preprocess_hydra(
    model: Hydra,
    image_path: str,
    device: torch.device,
) -> tuple[Tensor, Tensor]:
    """
    Preprocess an image for Hydra inference using the model's own pipeline.

    Uses libvips (pyvips) sRGB/ICC handling, aspect-preserving NaFlex resize,
    and patchification exactly as the Hydra project does, driven by the model's
    embedded ``ImageConfig`` (background, resize kernel, patch size, seqlen).

    Args:
        model: The loaded Hydra model.
        image_path: Path to the image file.
        device: Torch device to place the patch batch on.

    Returns:
        Tuple of (patches, sizes):
        - patches: uint8 tensor of shape ``[1, max_seqlen, patch_size^2 * 3]``
        - sizes: uint16 tensor of shape ``[1, 2]`` with (h_patches, w_patches)
    """
    img = model.load_image(image_path)
    patches, sizes = image.stack(
        [img],
        model.image_config.patch_size,
        model.image_config.max_seqlen,
        device=device,
    )
    return patches, sizes


def run_inference_hydra(
    model: Hydra,
    patches: Tensor,
    sizes: Tensor,
) -> Tensor:
    """
    Run a Hydra model forward pass, returning raw per-tag probabilities.

    The model head applies sigmoid internally (``logit=False``), so the returned
    tensor holds probabilities in ``[0, 1]``, one per tag, aligned to the label
    order from :func:`load_hydra_model`. Calibration / implication / thresholding
    is applied downstream by the caller.

    Args:
        model: The loaded Hydra model.
        patches: Patch batch from :func:`preprocess_hydra`.
        sizes: Patch-grid sizes from :func:`preprocess_hydra`.

    Returns:
        1-D float tensor of probabilities on the CPU (shape ``[num_tags]``).
    """
    print("InferenceHydra: Running inference...")
    start_inference = time.time()

    with torch.no_grad():
        output = model.forward(model.from_srgb(patches), sizes)[0]
        probabilities = output.float().cpu()

    end_inference = time.time()
    print(f"InferenceHydra: Inference took {end_inference - start_inference:.3f} seconds.")

    return probabilities
