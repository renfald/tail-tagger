from functools import cache
from typing import Callable, TypeAlias, cast, TYPE_CHECKING

try:
    from collections.abc import Buffer
except ImportError:
    if not TYPE_CHECKING:
        Buffer: TypeAlias = bytes | memoryview

import numpy as np
from numpy.typing import ArrayLike

import torch
from torch import Tensor

from einops import rearrange

from pyvips import Image, Source as VipsSource, cache_set_max
from pyvips.enums import Intent, Interpretation, Kernel, PCS

__all__ = (
    "Image", "Kernel",
    "Source", "Size", "Box", "Color", "ResizeFn", "CropFn",
    "open_srgb",
    "as_tensor", "spread", "patchify",
    "put", "put_patches",
    "unfold", "unfold_stack", "unfold_varlen",
    "stack", "varlen", "stack_to_varlen",
)

cache_set_max(0)

Source: TypeAlias = VipsSource | Image | Buffer | str
Size: TypeAlias = tuple[int, int] #hw
Box: TypeAlias = tuple[int, int, int, int] # ltrb
Color: TypeAlias = tuple[int | float, ...] | int | float
ResizeFn: TypeAlias = Callable[[Size], Size | None]
CropFn: TypeAlias = Callable[[Size], Box | None]

def _open_profile(
    source: Source,
    profile: str, depth: int,
    expect: Size | None,
    crop: CropFn | Box | None,
    resize: ResizeFn | Size | None,
    background: Color,
    kernel: Kernel,
    resize_luts: tuple[Image, Image] | None,
) -> Image:
    if isinstance(source, Image):
        img = source
    else:
        if isinstance(source, str):
            source = VipsSource.new_from_file(source)
        elif not isinstance(source, VipsSource):
            source = VipsSource.new_from_memory(source)

        img = Image.new_from_source(source, "")

    # Rotation happens last for efficiency, so track state.
    # This uses the exact same logic as vips_image_get_orientation_swap.
    if img.get_typeof("orientation"):
        orientation = img.get("orientation")
        rotated = isinstance(orientation, int) and 5 <= orientation <= 8
    else:
        rotated = False

    size = (img.height, img.width) if not rotated else (img.width, img.height)

    if expect is not None and size != expect:
        raise RuntimeError(f"Image is {size[1]}x{size[0]}, but expected {expect[1]}x{expect[0]} (rotated={rotated}).")

    if crop is not None and not isinstance(crop, tuple):
        crop = crop(size)

    if crop is not None:
        if crop == (0, 0, size[1], size[0]):
            crop = None
        else:
            left, top, right, bottom = crop
            assert 0 <= top < bottom <= size[0]
            assert 0 <= left < right <= size[1]

            size = (bottom - top, right - left)

            if rotated:
                crop = (top, left, size[0], size[1])
            else:
                crop = (left, top, size[1], size[0])

    if resize is not None and not isinstance(resize, tuple):
        resize = resize(size)

    if resize is not None:
        if resize == size:
            resize = None
        else:
            assert resize[0] > 0
            assert resize[1] > 0

            size = resize
            if rotated:
                resize = (resize[1], resize[0])

    if crop is not None:
        img = img.crop(*crop)

    img = img.icc_transform(
        profile, embedded=True,
        intent=Intent.RELATIVE,
        black_point_compensation=True,
        depth=depth,
    )

    if img.hasalpha():
        img = img.flatten(background=background)

    if resize is not None:
        if resize_luts is not None:
            img = img.maplut(resize_luts[0])

        img = img.resize(
            resize[1] / img.width,
            vscale=resize[0] / img.height,
            kernel=kernel, gap=3.0
        )

        if resize_luts is not None:
            img = img.maplut(resize_luts[1])

    img = img.autorot()
    assert (img.height, img.width) == size
    return img

def _srgb_to_rgb16(c: int) -> int:
    if c <= 10:
        v = (c * 257) / 12.92
    else:
        v = (((c + 14.025) / 269.025) ** 2.4) * 65535

    return int(round(v))

def _rgb16_to_srgb(c: int) -> int:
    if c <= 205:
        v = c * (12.92 / 257)
    else:
        v = ((c / 65535.0)**(1.0/2.4) * 269.025) - 14.025

    return int(round(v))

_LUT_SRGB_RGB16 = Image.new_from_array(np.asarray(
    [_srgb_to_rgb16(c) for c in range(0, 256)],
    dtype=np.uint16
))
_LUT_RGB16_SRGB = Image.new_from_array(np.asarray(
    [_rgb16_to_srgb(c) for c in range(0, 65536)],
    dtype=np.uint8
))

def open_srgb(
    source: Source,
    *,
    expect: Size | None = None,
    crop: CropFn | Box | None = None,
    resize: ResizeFn | Size | None = None,
    background: Color = 0,
    kernel: Kernel = Kernel.LANCZOS3,
    linear: bool = False,
) -> Image:
    return _open_profile(
        source, "srgb", 8,
        expect, crop, resize,
        background, kernel,
        (_LUT_SRGB_RGB16, _LUT_RGB16_SRGB) if linear else None,
    )

def as_tensor(img: ArrayLike) -> Tensor:
    return torch.from_numpy(np.asarray(img))

def put(img: ArrayLike, tensor: Tensor) -> None:
    np.copyto(tensor.numpy(), img, casting="no")

def put_patches(
    img: ArrayLike,
    patches: Tensor,
    patch_size: int,
    *,
    sizes: Tensor | None = None,
    valid: Tensor | None = None,
    clear_valid: bool = False
) -> Size:
    # Carefully structured so we perform a strided copy on views.
    source = rearrange(
        np.asarray(img),
        "... (h p1) (w p2) c -> ... h w p1 p2 c",
        p1=patch_size, p2=patch_size
    )
    h, w = source.shape[-5:-3]

    patches = rearrange(
        patches[..., :h*w, :],
        "... (h w) (p1 p2 c) -> ... h w p1 p2 c",
        h=h, w=w, p1=patch_size, p2=patch_size
    )

    put(source, patches)

    if sizes is not None:
        sizes[..., 0] = h
        sizes[..., 1] = w

    if valid is not None:
        if clear_valid:
            valid[..., h*w:] = False
        else:
            valid[..., :h*w] = True

    return h, w

def unfold(seq: Tensor, size: Size | Tensor, dim: int = -1) -> Tensor:
    if isinstance(size, Tensor):
        h = cast(int, size[0].item())
        w = cast(int, size[1].item())
    else:
        h, w = size

    return seq.narrow(dim, 0, h*w).unflatten(dim, (h, w))

def unfold_stack(seqs: Tensor, sizes: Tensor) -> list[Tensor]:
    assert seqs.ndim == 3

    return [
        unfold(seq, size, 1)
        for seq, size in zip(seqs.unbind(0), sizes.tolist(), strict=True)
    ]

def unfold_varlen(vseq: Tensor, sizes: Tensor) -> list[Tensor]:
    assert vseq.ndim == 2
    indices = sizes[:-1].prod(-1).cumsum(-1, dtype=torch.int64)

    return [
        seq.unflatten(0, size)
        for seq, size in zip(
            torch.tensor_split(vseq, indices, 0),
            sizes.tolist(),
            strict=True
        )
    ]

def spread(img: Tensor, patch_size: int) -> Tensor:
    return rearrange(
        img, f"... (h p1) (w p2) c -> ... h w p1 p2 c",
        p1=patch_size, p2=patch_size
    )

def patchify(
    img: ArrayLike | Tensor,
    patch_size: int,
    *,
    ensure_batch_dim: bool = True,
    dtype: torch.dtype | None = None
) -> Tensor:
    if not isinstance(img, Tensor):
        img = as_tensor(img)

    if ensure_batch_dim and img.ndim == 3:
        img = img.unsqueeze(0)

    img = spread(img, patch_size)

    if dtype is not None and dtype != img.dtype:
        img = img.to(dtype=dtype, memory_format=torch.contiguous_format)

    return img.flatten(-3)

def stack(
    images: list[Tensor],
    patch_size: int,
    max_seq: int,
    *,
    max_n: int = 0,
    channels: int = 3,
    device: torch.device | str | None = None,
    dtype: torch.dtype | None = None
) -> tuple[Tensor, Tensor]:
    if device is None:
        device = images[0].device
    if dtype is None:
        dtype = images[0].dtype

    batch = torch.empty(
        len(images), max_seq, patch_size * patch_size * channels,
        device=device, dtype=dtype
    )
    sizes = torch.empty(
        len(images), 2,
        device="cpu", dtype=torch.uint16
    )

    if max_n > 1:
        torch._dynamo.mark_dynamic(batch, 0, min=1, max=max_n)
        torch._dynamo.mark_dynamic(sizes, 0, min=1, max=max_n)

    srcs: list[Tensor] = []
    dests: list[Tensor] = []
    zero: list[Tensor] = []
    for idx, img in enumerate(images):
        img = spread(img, patch_size)
        assert img.ndim == 5

        h, w = img.shape[:2]
        sizes[idx, 0] = h
        sizes[idx, 1] = w
        seqlen = h*w

        srcs.append(img)
        dests.append(batch[idx, :seqlen].view(img.shape))

        if seqlen < max_seq:
            zero.append(batch[idx, seqlen:])

    torch._foreach_copy_(dests, srcs, non_blocking=True)
    if zero:
        torch._foreach_zero_(zero)

    return batch, sizes

def varlen(
    images: list[Tensor],
    patch_size: int,
    *,
    max_n: int = 0,
    channels: int = 3,
    device: torch.device | str | None = None,
    dtype: torch.dtype | None = None
) -> tuple[Tensor, Tensor, Tensor]:
    if device is None:
        device = images[0].device
    if dtype is None:
        dtype = images[0].dtype

    patch_n = patch_size * patch_size * channels

    sizes = torch.empty(
        len(images), 2,
        device="cpu", dtype=torch.uint16
    )

    cu_seq = torch.empty(
        len(images) + 1,
        device="cpu", dtype=torch.int32
    )
    cu_seq[0] = 0

    if max_n > 1:
        torch._dynamo.mark_dynamic(sizes, 0, min=1, max=max_n)
        torch._dynamo.mark_dynamic(cu_seq, 0, min=2, max=max_n+1)

    srcs: list[Tensor] = []
    for idx, img in enumerate(images):
        img = spread(img, patch_size)
        assert img.ndim == 5

        h, w = img.shape[:2]
        sizes[idx, 0] = h
        sizes[idx, 1] = w

        cu_seq[idx + 1] = cu_seq[idx] + h*w
        srcs.append(img)

    cu_seq_d = cu_seq.to(device=device, non_blocking=True)

    if len(srcs) == 1:
        batch = srcs.pop().reshape(-1, patch_n)
        batch = batch.to(device=device, dtype=dtype, non_blocking=True)
    else:
        batch = torch.empty(
            cast(int, cu_seq[-1].item()), patch_n,
            device=device, dtype=dtype
        )

        dests = [
            dest.view(src.shape)
            for src, dest in zip(srcs, batch.tensor_split(cu_seq[1:-1].long()))
        ]
        torch._foreach_copy_(dests, srcs, non_blocking=True)

    torch._dynamo.mark_dynamic(batch, 0)
    return batch, sizes, cu_seq_d

def stack_to_varlen(
    stack: Tensor, sizes: Tensor,
    *,
    device: torch.device | str | None = None,
    dtype: torch.dtype | None = None
) -> tuple[Tensor, Tensor]:
    assert stack.ndim == 3
    assert sizes.ndim == 2
    assert sizes.size(0) == stack.size(0)

    if device is None:
        device = stack.device
    if dtype is None:
        dtype = stack.dtype

    cu_seq = torch.empty(
        stack.size(0) + 1,
        device="cpu", dtype=torch.int32
    )
    cu_seq[0] = 0

    srcs: list[Tensor] = []
    for idx, (h, w) in enumerate(sizes.tolist()):
        seqlen = h*w
        cu_seq[idx + 1] = cu_seq[idx] + seqlen
        srcs.append(stack[idx, :seqlen])

    cu_seq_d = cu_seq.to(device=stack.device, non_blocking=True)

    if len(srcs) == 1:
        batch = srcs.pop().to(device=device, dtype=dtype, non_blocking=True)
    else:
        batch = torch.empty(
            cast(int, cu_seq[-1].item()), stack.size(-1),
            device=device, dtype=dtype
        )

        dests = batch.tensor_split(cu_seq[1:-1].long())
        torch._foreach_copy_(dests, srcs, non_blocking=True)

    torch._dynamo.mark_dynamic(batch, 0)
    return batch, cu_seq_d

def srgb_to_rgb(srgb: Tensor) -> Tensor:
    return torch.where(
        srgb <= 0.04045,
        srgb * (1.0/12.92),
        ((srgb + 0.055) * (1.0/1.055))**2.4
    )

def rgb_to_srgb(rgb: Tensor) -> Tensor:
    return torch.where(
        rgb <= 0.0031308,
        rgb * 12.92,
        1.055 * rgb**(1.0/2.4) - 0.055
    )

def rgb_to_grey(rgb: Tensor, *, keepdim: bool = False) -> Tensor:
    grey = torch.linalg.vecdot(rgb, torch.tensor(
        (0.2126, 0.7152, 0.0722),
        device=rgb.device, dtype=rgb.dtype
    ))

    if keepdim:
        grey = grey.unsqueeze(-1)

    return grey
