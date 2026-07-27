"""
Inference module for different classifier model architectures.

This module provides a unified interface for loading and running inference
with different classifier models (JTP-2, JTP-3, etc.).
"""

from .jtp2_inference import (
    load_jtp2_model,
    preprocess_jtp2,
    run_inference_jtp2,
)

from .hydra_inference import (
    load_hydra_model,
    preprocess_hydra,
    run_inference_hydra,
    HydraMetadataMissingError,
)

__all__ = [
    # JTP-2
    "load_jtp2_model",
    "preprocess_jtp2",
    "run_inference_jtp2",
    # Hydra (JTP-3 Hydra + Hydra 3.5, via vendored package)
    "load_hydra_model",
    "preprocess_hydra",
    "run_inference_hydra",
    "HydraMetadataMissingError",
]
