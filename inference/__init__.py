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

from .jtp3_inference import (
    load_jtp3_model,
    preprocess_jtp3,
    run_inference_jtp3,
)

__all__ = [
    # JTP-2
    "load_jtp2_model",
    "preprocess_jtp2",
    "run_inference_jtp2",
    # JTP-3
    "load_jtp3_model",
    "preprocess_jtp3",
    "run_inference_jtp3",
]
