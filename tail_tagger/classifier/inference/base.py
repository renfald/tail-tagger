"""
Base classes and type definitions for inference modules.
"""

from abc import ABC, abstractmethod
from typing import Any

import torch


class ModelLoader(ABC):
    """Abstract base class for model loaders."""

    @abstractmethod
    def load_model(
        self,
        model_path: str,
        device: torch.device,
        **kwargs: Any
    ) -> tuple[torch.nn.Module, list[str]]:
        """
        Load a model from disk.

        Args:
            model_path: Path to the model file
            device: Torch device to load the model onto
            **kwargs: Additional loader-specific arguments

        Returns:
            Tuple of (model, list of tag names)
        """
        pass

    @abstractmethod
    def preprocess(self, image_path: str, **kwargs: Any) -> Any:
        """
        Preprocess an image for inference.

        Args:
            image_path: Path to the image file
            **kwargs: Additional preprocessing arguments

        Returns:
            Preprocessed data ready for model input
        """
        pass

    @abstractmethod
    def run_inference(
        self,
        model: torch.nn.Module,
        preprocessed_data: Any,
        device: torch.device,
        **kwargs: Any
    ) -> torch.Tensor:
        """
        Run inference with the model.

        Args:
            model: The loaded model
            preprocessed_data: Output from preprocess()
            device: Torch device
            **kwargs: Additional inference arguments

        Returns:
            Tensor of probabilities for each tag
        """
        pass
