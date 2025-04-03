import torch
from PIL import Image
from torchvision.transforms import transforms, InterpolationMode
import torchvision.transforms.functional as TF
from typing import Tuple, Optional

class Fit(torch.nn.Module):
    def __init__(self, bounds: Tuple[int, int] | int, interpolation=InterpolationMode.LANCZOS, grow: bool = True, pad: float | None = None):
        super().__init__()
        self.bounds = (bounds, bounds) if isinstance(bounds, int) else bounds
        self.interpolation = interpolation
        self.grow = grow
        self.pad = pad

    def forward(self, img: Image.Image) -> Image.Image:
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
        wnew = min(round(wimg * scale), hbound)

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
        return f"{self.__class__.__name__}(bounds={self.bounds}, interpolation={self.interpolation.value}, grow={self.grow}, pad={self.pad})"

class CompositeAlpha(torch.nn.Module):
    def __init__(self, background: Tuple[float, float, float] | float) -> None:
        super().__init__()
        self.background = (background, background, background) if isinstance(background, float) else background
        self.background = torch.tensor(self.background).unsqueeze(1).unsqueeze(2)

    def forward(self, img: torch.Tensor) -> torch.Tensor:
        if img.shape[-3] == 3:
            return img
import torch
from PIL import Image
from torchvision.transforms import transforms, InterpolationMode
import torchvision.transforms.functional as TF

class Fit(torch.nn.Module):
    """
    A custom transformation class to fit an image within specified bounds while maintaining aspect ratio.
    Optionally pads the image to the specified size.
    """
    def __init__(self, bounds: Tuple[int, int] | int, interpolation=InterpolationMode.LANCZOS, grow: bool = True, pad: Optional[float] = None) -> None:
        super().__init__()
        self.bounds = (bounds, bounds) if isinstance(bounds, int) else bounds
        self.interpolation = interpolation
        self.grow = grow
        self.pad = pad

    def forward(self, img: Image.Image) -> Image.Image:
        """
        Apply the fit transformation to an image.
        """
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
        return f"{self.__class__.__name__}(bounds={self.bounds}, interpolation={self.interpolation.value}, grow={self.grow}, pad={self.pad})"

class CompositeAlpha(torch.nn.Module):
    """
    A custom transformation class to composite an image with an alpha channel onto a solid background.
    """
    def __init__(self, background: Tuple[float, float, float] | float) -> None:
        super().__init__()
        self.background = (background, background, background) if isinstance(background, float) else background
        self.background = torch.tensor(self.background).unsqueeze(1).unsqueeze(2)

    def forward(self, img: torch.Tensor) -> torch.Tensor:
        """
        Apply the composite alpha transformation to an image tensor.
        """
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

def get_transform():
    return transforms.Compose([
        Fit((384, 384)),
        transforms.ToTensor(),
        CompositeAlpha(0.5),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
        transforms.CenterCrop((384, 384)),
    ])
