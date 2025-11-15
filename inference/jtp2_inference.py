"""
JTP-2 (PILOT/PILOT2) inference module.

This module handles model loading, preprocessing, and inference for
JTP_PILOT and JTP_PILOT2 models (SigLIP ViT architecture).
"""

import json
import time
from typing import Tuple

import torch
import timm
import safetensors.torch
from PIL import Image
from torchvision.transforms import transforms, InterpolationMode
import torchvision.transforms.functional as TF


# --- Custom Head for JTP_PILOT2 ---
class GatedHead(torch.nn.Module):
    """Custom gated classification head for JTP_PILOT2."""

    def __init__(self, num_features: int, num_classes: int):
        super().__init__()
        self.num_classes = num_classes
        self.linear = torch.nn.Linear(num_features, num_classes * 2)
        self.act = torch.nn.Sigmoid()
        self.gate = torch.nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Assuming x is batch x num_features
        x = self.linear(x)  # Output shape: batch x (num_classes * 2)
        # Split the output into two parts for activation and gating
        activation_output = x[:, :self.num_classes]
        gate_output = x[:, self.num_classes:]
        # Apply activation and gating
        x = self.act(activation_output) * self.gate(gate_output)
        return x


# --- Image Preprocessing Transforms ---
class Fit(torch.nn.Module):
    """
    A custom transformation class to fit an image within specified bounds
    while maintaining aspect ratio. Optionally pads the image to the specified size.
    """

    def __init__(
        self,
        bounds: Tuple[int, int] | int,
        interpolation=InterpolationMode.LANCZOS,
        grow: bool = True,
        pad: float | None = None
    ) -> None:
        super().__init__()
        self.bounds = (bounds, bounds) if isinstance(bounds, int) else bounds
        self.interpolation = interpolation
        self.grow = grow
        self.pad = pad

    def forward(self, img: Image.Image) -> Image.Image:
        """Apply the fit transformation to an image."""
        wimg, himg = img.size
        hbound, wbound = self.bounds

        hscale = hbound / himg
        wscale = wbound / wimg

        if not self.grow:
            hscale = min(hscale, 1.0)
            wscale = min(wscale, 1.0)

        scale = min(hscale, wscale)
        if scale == 1.0:
            return img

        hnew = min(round(himg * scale), hbound)
        wnew = min(round(wimg * scale), wbound)

        img = TF.resize(img, (hnew, wnew), self.interpolation)

        if self.pad is None:
            return img

        hpad = hbound - hnew
        wpad = wbound - wnew

        tpad = hpad // 2
        bpad = hpad - tpad

        lpad = wpad // 2
        rpad = wpad - lpad

        return TF.pad(img, (lpad, tpad, rpad, bpad), self.pad)

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(bounds={self.bounds}, "
                f"interpolation={self.interpolation.value}, grow={self.grow}, pad={self.pad})")


class CompositeAlpha(torch.nn.Module):
    """
    A custom transformation class to composite an image with an alpha channel
    onto a solid background.
    """

    def __init__(self, background: Tuple[float, float, float] | float) -> None:
        super().__init__()
        self.background = (background, background, background) if isinstance(background, float) else background
        self.background = torch.tensor(self.background).unsqueeze(1).unsqueeze(2)

    def forward(self, img: torch.Tensor) -> torch.Tensor:
        """Apply the composite alpha transformation to an image tensor."""
        if img.shape[-3] == 3:
            return img

        alpha = img[..., 3, None, :, :]
        img[..., :3, :, :] *= alpha

        background = self.background.expand(-1, img.shape[-2], img.shape[-1])
        if background.ndim == 1:
            background = background[:, None, None]
        elif background.ndim == 2:
            background = background[None, :, :]

        img[..., :3, :, :] += (1.0 - alpha) * background
        return img[..., :3, :, :]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(background={self.background})"


def get_jtp2_transform():
    """Get the preprocessing transform pipeline for JTP-2 models."""
    return transforms.Compose([
        Fit((384, 384)),
        transforms.ToTensor(),
        CompositeAlpha(0.5),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
        transforms.CenterCrop((384, 384)),
    ])


# --- Model Loading ---
def load_jtp2_model(
    model_path: str,
    tags_path: str,
    device: torch.device,
    model_id: str
) -> tuple[torch.nn.Module, list[str]]:
    """
    Load a JTP-2 (PILOT/PILOT2) model from disk.

    Args:
        model_path: Path to the .safetensors model file
        tags_path: Path to the tags.json file
        device: Torch device to load the model onto
        model_id: Model identifier ("JTP_PILOT" or "JTP_PILOT2")

    Returns:
        Tuple of (model, list of tag names)
    """
    load_start_time = time.time()

    # Load tags
    print(f"LoadJTP2: Loading tags from {tags_path}...")
    with open(tags_path, 'r', encoding='utf-8') as f:
        allowed_tags_dict = json.load(f)
    # allowed_tags_dict is {tag_name: index}
    # Sort by index to get tag list in correct order
    allowed_tags = [tag for tag, idx in sorted(allowed_tags_dict.items(), key=lambda x: x[1])]
    print(f"LoadJTP2: Loaded {len(allowed_tags)} tags.")

    # Create model architecture
    print("LoadJTP2: Creating ViT model structure...")
    model = timm.create_model(
        "vit_so400m_patch14_siglip_384.webli",
        pretrained=False,
        num_classes=len(allowed_tags),
    )
    print(f"LoadJTP2: Loading model weights from {model_path}...")

    # Replace head for JTP_PILOT2
    if model_id == "JTP_PILOT2":
        print("LoadJTP2: Replacing model head with GatedHead for JTP_PILOT2.")
        num_features = model.head.in_features
        model.head = GatedHead(num_features, len(allowed_tags))

    # Load weights
    state_dict = safetensors.torch.load_file(model_path, device=str(device))
    model.load_state_dict(state_dict)
    model.eval()
    model.to(device)
    print(f"LoadJTP2: Model loaded successfully to {device}.")

    # Apply performance optimizations if applicable
    if device.type == 'cuda' and torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 7:
        model.to(dtype=torch.float16)
        print("LoadJTP2: Applied float16 optimization.")

    load_end_time = time.time()
    print(f"LoadJTP2: Model and tags loaded in {load_end_time - load_start_time:.2f} seconds.")

    return model, allowed_tags


# --- Preprocessing ---
def preprocess_jtp2(image_path: str) -> torch.Tensor:
    """
    Preprocess an image for JTP-2 inference.

    Args:
        image_path: Path to the image file

    Returns:
        Preprocessed tensor ready for model input (shape: [1, 3, 384, 384])
    """
    transform = get_jtp2_transform()
    image = Image.open(image_path).convert("RGBA")
    tensor = transform(image)
    tensor = tensor.unsqueeze(0)  # Add batch dimension
    return tensor


# --- Inference ---
def run_inference_jtp2(
    model: torch.nn.Module,
    tensor: torch.Tensor,
    device: torch.device,
    model_id: str
) -> torch.Tensor:
    """
    Run inference with a JTP-2 model.

    Args:
        model: The loaded model
        tensor: Preprocessed image tensor (shape: [1, 3, 384, 384])
        device: Torch device
        model_id: Model identifier ("JTP_PILOT" or "JTP_PILOT2")

    Returns:
        Tensor of probabilities for each tag (shape: [num_classes])
    """
    print("InferenceJTP2: Running inference...")
    start_inference = time.time()

    # Move tensor to device
    tensor = tensor.to(device)

    # Apply float16 if model is float16
    if next(model.parameters()).dtype == torch.float16:
        tensor = tensor.to(dtype=torch.float16)

    with torch.no_grad():
        logits = model(tensor)

    end_inference = time.time()
    print(f"InferenceJTP2: Inference took {end_inference - start_inference:.3f} seconds.")

    # Post-processing: Convert logits to probabilities
    if model_id == "JTP_PILOT2":
        print("InferenceJTP2: Using direct output probabilities for JTP_PILOT2.")
        # Output is already probabilities from GatedHead
        probabilities = logits[0]  # Remove batch dim
    else:
        print("InferenceJTP2: Applying sigmoid to logits.")
        # Apply Sigmoid for models like JTP_PILOT (standard head)
        probabilities = torch.nn.functional.sigmoid(logits[0])  # Remove batch dim

    return probabilities
