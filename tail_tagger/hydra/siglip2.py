from collections import defaultdict
from itertools import pairwise, product
from typing import Callable, Collection, Iterable, TypedDict, MutableMapping, cast

from ._compat import NotRequired
from warnings import warn

import torch
from torch import Tensor
from torch.nn import Module, ModuleList, LayerNorm, Parameter, Linear, Identity
from torch.nn.functional import interpolate, scaled_dot_product_attention, gelu

try:
    from torch.nn.attention.varlen import varlen_attn
    HAS_VARLEN_ATTN = True
except ImportError:
    HAS_VARLEN_ATTN = False

from einops import rearrange

from .cufork import CuFork

__all__ = ("HAS_VARLEN_ATTN", "NaFlexVit")

class NaFlexEmbeds(Module):
    def __init__(
        self, *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.pos_embed = Parameter(torch.empty(1, 16, 16, 1152, device=device, dtype=dtype))
        self.proj = Linear(768, 1152, device=device, dtype=dtype)

        self.cache: MutableMapping[tuple[int, int], Tensor] | None = None
        self.pos_embed_cast: torch.dtype | None = None

    @torch.compiler.disable()
    def enable_cache(
        self, enabled: bool = True, *,
        ty: Callable[[], MutableMapping[tuple[int, int], Tensor]] = dict
    ) -> None:
        if not enabled:
            self.cache = None
        elif self.cache is None:
            self.cache = ty()

    @torch.compiler.disable()
    def cpu_support(self) -> None:
        # https://github.com/pytorch/pytorch/pull/175490

        if (
            self.pos_embed_cast is not None
            or self.pos_embed.device.type != "cpu"
            or self.pos_embed.dtype not in (torch.float16, torch.bfloat16)
        ):
            return

        self.pos_embed_cast = self.pos_embed.dtype
        self.pos_embed.data = self.pos_embed.data.float()

    def forward(self, patches: Tensor, sizes: Tensor, *, compute_valid: bool = True) -> tuple[Tensor, Tensor | None]:
        # ... S C, ... 2
        patches = self.proj(patches)
        return self._apply_pos_embed_padded(patches, sizes, compute_valid)

    def forward_uniform(self, patches: Tensor) -> Tensor:
        # ... H W C
        patches = self.proj(patches)
        return self._apply_pos_embed_uniform(patches)

    def forward_varlen(self, patches: Tensor, sizes: Tensor) -> Tensor:
        # S C, N 2
        patches = self.proj(patches)
        return self._apply_pos_embed_varlen(patches, sizes)

    def _apply_pos_embed_uniform(self, patches: Tensor) -> Tensor:
        h, w = patches.shape[-3:-1]
        patches = rearrange(patches, "... h w c -> ... (h w) c")
        return patches.add_(self._get_pos_embed((h, w)))

    @torch.compiler.disable()
    def _apply_pos_embed_padded(self, patches: Tensor, sizes: Tensor, compute_valid: bool) -> tuple[Tensor, Tensor | None]:
        groups: dict[tuple[int, int], list[Tensor]] = defaultdict(list)
        zero: list[Tensor] = []

        valid: Tensor | None = None
        if compute_valid:
            valid = torch.ones(patches.shape[:-1], device=patches.device, dtype=torch.bool)

        for idx, (seq, size, invalid) in enumerate(self._unpad(patches, sizes, valid)):
            groups[size].append(seq)

            if invalid is not None:
                zero.append(invalid)

        with CuFork(patches) as fork:
            if zero:
                torch._foreach_zero_(zero)

            for shape, group in groups.items():
                fork.fork()
                torch._foreach_add_(group, [self._get_pos_embed(shape)] * len(group))

        return patches, valid

    @torch.compiler.disable()
    def _apply_pos_embed_varlen(self, patches: Tensor, sizes: Tensor) -> Tensor:
        groups: dict[tuple[int, int], list[Tensor]] = defaultdict(list)

        offset = 0
        for h, w in sizes.tolist():
            start = offset
            offset += h*w
            groups[(h, w)].append(patches[start:offset])

        with CuFork(patches) as fork:
            for shape, group in groups.items():
                fork.fork()
                torch._foreach_add_(group, [self._get_pos_embed(shape)] * len(group))

        return patches

    @staticmethod
    def _unpad(patches: Tensor, sizes: Tensor, valid: Tensor | None) -> Iterable[tuple[Tensor, tuple[int, int], Tensor | None]]:
        if patches.ndim == 2:
            patches = patches.unsqueeze(0)
            valid = valid.unsqueeze(0) if valid is not None else None
        else:
            assert patches.ndim > 2

        prefix = patches.shape[:-2]
        sizes = sizes.cpu().broadcast_to((*prefix, 2))

        for idxs in product(*(range(dim) for dim in prefix)):
            h, w = sizes[idxs].tolist()
            seqlen = h*w

            yield (
                patches[idxs + (slice(None, seqlen),)], #type: ignore[index]
                (h, w),
                valid[idxs + (slice(seqlen, None),)] if valid is not None and seqlen < valid.size(-1) else None # type: ignore[index]
            )

    @torch.compiler.disable()
    def _get_pos_embed(self, shape: tuple[int, int]) -> Tensor:
        if self.cache is not None:
            if self.training and self.pos_embed.requires_grad:
                warn("Position embeding cache enabled during training.")

            if (pos_embed := self.cache.get(shape)) is not None:
                return pos_embed

        if shape == (16, 16):
            pos_embed = rearrange(self.pos_embed, "1 h w c -> (h w) c")
        else:
            self.cpu_support()

            pos_embed = rearrange(self.pos_embed, "1 h w c -> 1 c h w")
            pos_embed = interpolate(pos_embed, shape, mode="bilinear", antialias=True)
            pos_embed = rearrange(pos_embed, "1 c h w -> (h w) c")

        if self.pos_embed_cast is not None:
            pos_embed = pos_embed.to(
                dtype=self.pos_embed_cast,
                memory_format=torch.contiguous_format
            )

        if self.cache is not None:
            pos_embed = pos_embed.contiguous()
            self.cache[shape] = pos_embed

        return pos_embed

class NaFlexBlock(Module):
    def __init__(
        self, *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.attn = NaFlexAttn(device=device, dtype=dtype)
        self.mlp = NaFlexMlp(device=device, dtype=dtype)
        self.norm1 = LayerNorm(1152, device=device, dtype=dtype)
        self.norm2 = LayerNorm(1152, device=device, dtype=dtype)

    def forward(self, x: Tensor, attn_mask: Tensor) -> Tensor:
        x = x + self.attn(self.norm1(x), attn_mask)
        x = x + self.mlp(self.norm2(x))
        return x

    def forward_varlen(self, x: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        x = x + self.attn.forward_varlen(self.norm1(x), cu_seq, max_seq)
        x = x + self.mlp(self.norm2(x))
        return x

class NaFlexAttn(Module):
    def __init__(
        self, *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.qkv = Linear(1152, 3456, device=device, dtype=dtype)
        setattr(self.qkv.weight, "rr_muon_chunks", (3, 16))

        self.proj = Linear(1152, 1152, device=device, dtype=dtype)

    def forward(self, x: Tensor, attn_mask: Tensor) -> Tensor:
        x = self.qkv(x)

        q, k, v = rearrange(x, "... s (n h e) -> n ... h s e", n=3, h=16).unbind(0)
        x = scaled_dot_product_attention(q, k, v, attn_mask=attn_mask)
        x = rearrange(x, "... h s e -> ... s (h e)")

        x = self.proj(x)
        return x

    def forward_varlen(self, x: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        x = self.qkv(x)

        q, k, v = rearrange(x, "s (n h e) -> n s h e", n=3, h=16).unbind(0)
        x = cast(Tensor, varlen_attn(q, k, v, cu_seq, cu_seq, max_seq, max_seq))
        x = rearrange(x, "s h e -> s (h e)")

        x = self.proj(x)
        return x

class NaFlexMlp(Module):
    def __init__(
        self, *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.fc1 = Linear(1152, 4304, device=device, dtype=dtype)
        self.fc2 = Linear(4304, 1152, device=device, dtype=dtype)

    def forward(self, x: Tensor) -> Tensor:
        x = self.fc1(x)
        x = gelu(x, approximate="tanh")
        x = self.fc2(x)
        return x

class NaFlexFeatures(TypedDict):
    features: NotRequired[Tensor]
    intermediates: NotRequired[list[Tensor]]
    valid: NotRequired[Tensor | None]

class NaFlexFeaturesVarlen(TypedDict):
    features: NotRequired[Tensor]
    intermediates: NotRequired[list[Tensor]]
    cu_seq: NotRequired[Tensor]
    max_seq: NotRequired[int]

class NaFlexVit(Module):
    def __init__(
        self, *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.embeds = NaFlexEmbeds(device=device, dtype=dtype)
        self.blocks = ModuleList(
            NaFlexBlock(device=device, dtype=dtype)
            for _ in range(0, 27)
        )
        self.norm = LayerNorm(1152, device=device, dtype=dtype)

        self.attn_pool: Module = Identity()
        self.head: Module = Identity()
        self.emb_head: Module = Identity()

    def forward_features(
        self, x: Tensor,
        sizes: Tensor | None = None,
        valid: Tensor | None = None,
        *,
        intermediates: Collection[int] = (),
        intermediates_only: bool = False,
        norm_intermediates: bool = False,
    ) -> NaFlexFeatures:
        if sizes is None:
            x = self.embeds.forward_uniform(x)
            if valid is not None:
                valid = valid.flatten(-2)
        elif valid is None:
            x, valid = self.embeds(x, sizes, compute_valid=True)
        else:
            x, _ = self.embeds(x, sizes, compute_valid=False)

        out: NaFlexFeatures = { "valid": valid }
        self._forward_blocks(
            "forward", out, x, self._attn_mask(valid),
            intermediates=intermediates,
            intermediates_only=intermediates_only,
            norm_intermediates=norm_intermediates,
        )
        return out

    def forward_features_varlen(
        self, x: Tensor,
        sizes: Tensor,
        cu_seq: Tensor,
        max_seq: int = 1024,
        *,
        intermediates: Collection[int] = (),
        intermediates_only: bool = False,
        norm_intermediates: bool = False,
    ) -> NaFlexFeaturesVarlen:
        x = self.embeds.forward_varlen(x, sizes)

        out: NaFlexFeaturesVarlen = { "cu_seq": cu_seq, "max_seq": max_seq }
        self._forward_blocks(
            "forward_varlen", out, x, cu_seq, max_seq,
            intermediates=intermediates,
            intermediates_only=intermediates_only,
            norm_intermediates=norm_intermediates,
        )
        return out

    def _forward_blocks(
        self, fn: str, out: NaFlexFeatures | NaFlexFeaturesVarlen,
        x: Tensor, *args,
        intermediates: Collection[int],
        intermediates_only: bool,
        norm_intermediates: bool,
    ) -> None:
        stop_at = max(
            idx if idx >= 0 else 27 + idx
            for idx in intermediates
        ) if intermediates_only else -1

        saved: list[Tensor] = []
        for idx, block in enumerate(self.blocks):
            x = getattr(block, fn)(x, *args)

            if idx in intermediates or (-26 + idx) in intermediates:
                if norm_intermediates:
                    saved.append(self.norm(x))
                else:
                    saved.append(x)

            if idx == stop_at:
                break

        if intermediates:
            out["intermediates"] = saved

        if not intermediates_only:
            if norm_intermediates and (26 in intermediates or -1 in intermediates):
                out["features"] = saved[-1]
            else:
                out["features"] = self.norm(x)

    def forward_head(self, features: Tensor, valid: Tensor | None) -> Tensor:
        return self.head(self.attn_pool(features, self._attn_mask(valid)))

    def forward_head_varlen(self, features: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        return self.head(self.attn_pool.forward_varlen(features, cu_seq, max_seq)) # type: ignore

    def forward_emb_head(self, features: Tensor, valid: Tensor | None) -> Tensor:
        return self.emb_head(
            self.attn_pool.forward_unpooled(features, self._attn_mask(valid)), # type: ignore
            valid
        )

    def forward_emb_head_varlen(self, features: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        return self.emb_head.forward_varlen(
            self.attn_pool.forward_unpooled_varlen(features, cu_seq, max_seq), # type: ignore
            cu_seq, max_seq
        ) # type: ignore

    def forward(self, x: Tensor, sizes: Tensor | None = None, valid: Tensor | None = None) -> Tensor:
        # ... H W C, None, ... H W
        # ... S C, ... S 2, ... S

        output = self.forward_features(x, sizes, valid)
        return self.forward_head(output.pop("features"), output.pop("valid"))

    def forward_varlen(self, x: Tensor, sizes: Tensor, cu_seq: Tensor, max_seq: int = 1024) -> Tensor:
        # S C, N 2, N+1

        output = self.forward_features_varlen(x, sizes, cu_seq, max_seq)
        return self.forward_head_varlen(output.pop("features"), output.pop("cu_seq"), output.pop("max_seq"))

    def forward_embedding(self, x: Tensor, sizes: Tensor | None = None, valid: Tensor | None = None) -> Tensor:
        # ... H W C, None, ... H W
        # ... S C, ... S 2, ... S

        output = self.forward_features(x, sizes, valid)
        return self.forward_emb_head(output.pop("features"), output.pop("valid"))

    def forward_embedding_varlen(self, x: Tensor, sizes: Tensor, cu_seq: Tensor, max_seq: int = 1024) -> Tensor:
        # S C, N 2, N+1

        output = self.forward_features_varlen(x, sizes, cu_seq, max_seq)
        return self.forward_emb_head_varlen(output.pop("features"), output.pop("cu_seq"), output.pop("max_seq"))

    @staticmethod
    def _attn_mask(valid: Tensor | None) -> Tensor | None:
        return valid[..., None, None, :] if valid is not None else None

    def from_srgb(self, seq: Tensor, *, inplace: bool = True) -> Tensor:
        if seq.device != self.embeds.proj.weight.device:
            seq = seq.to(device=self.embeds.proj.weight.device, non_blocking=True)
            inplace = True

        if seq.dtype != self.embeds.proj.weight.dtype:
            seq = seq.to(dtype=self.embeds.proj.weight.dtype)
            inplace = True

        if inplace:
            seq.div_(127.5)
        else:
            seq = seq / 127.5

        return seq.sub_(1.0)

    def compile(self, *args, **kwargs) -> None:
        for item in dir(self):
            if item.startswith("forward") or item == "from_srgb":
                setattr(self, item, torch.compile(getattr(self, item), *args, **kwargs))
