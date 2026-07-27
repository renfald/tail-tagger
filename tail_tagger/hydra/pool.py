import re
from math import sqrt
from typing import Any, Iterable, MutableSequence, cast

from ._compat import Self

import torch
from torch import Tensor
from torch.nn import (
    Module, ModuleList, Parameter, Buffer,
    Linear, LayerNorm, RMSNorm, Dropout, Flatten,
    init
)
from torch.nn.functional import scaled_dot_product_attention, normalize, linear

try:
    from torch.nn.attention.varlen import varlen_attn
except ImportError:
    pass

from einops import rearrange

from .glu import GLU, SwiGLU, SpGLU

__all__ = ("HydraPool",)

class _FeedForward(Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int = -1,
        *,
        glu: type[GLU],
        affine: bool = False,
        dropout: float = 0.0,
        device: torch.device | str | None,
        dtype: torch.dtype | None,
    ) -> None:
        super().__init__()

        if output_dim == -1:
            output_dim = input_dim

        self.norm = LayerNorm(
            input_dim, elementwise_affine=affine,
            device=device, dtype=dtype
        )
        self.proj_in = glu(
            input_dim, hidden_dim, dropout=dropout,
            device=device, dtype=dtype
        )
        self.proj_out = Linear(
            hidden_dim, output_dim, bias=False,
            device=device, dtype=dtype
        )

    def forward(self, x: Tensor) -> Tensor:
        x = self.norm(x)
        x = self.proj_in(x)
        x = self.proj_out(x)
        return x

class _MidBlock(Module):
    def __init__(
        self,
        n_classes: int,
        attn_dim: int,
        head_dim: int,
        ff_dim: int,
        *,
        glu: type[GLU],
        ff_dropout: float,
        device: torch.device | str | None,
        dtype: torch.dtype | None,
    ) -> None:
        super().__init__()

        self.head_dim = head_dim

        self.q_proj = Linear(
            attn_dim, attn_dim, bias=False,
            device=device, dtype=dtype
        )
        setattr(self.q_proj.weight, "rr_muon_chunks", (1, attn_dim // head_dim))

        self.q_norm = RMSNorm(head_dim, eps=1e-5, elementwise_affine=False)

        self.o_proj = Linear(
            attn_dim, attn_dim, bias=False,
            device=device, dtype=dtype
        )

        self.ff = _FeedForward(
            attn_dim, ff_dim,
            glu=glu,
            dropout=ff_dropout,
            device=device, dtype=dtype,
        )

    def _forward_q(self, x: Tensor, order: str = "... h s") -> Tensor:
        x = self.q_proj(x)
        x = rearrange(x, f"... s (h e) -> {order} e", e=self.head_dim)
        x = self.q_norm(x)
        return x

    def _forward_attn(self, x: Tensor, k: Tensor, v: Tensor, attn_mask: Tensor | None) -> Tensor:
        #sv = rearrange(x.detach(), "... s (h e) -> ... h s e", e=self.head_dim)

        x = self._forward_q(x)
        x = scaled_dot_product_attention(x, k, v, attn_mask=attn_mask)
        #x = self._xsa(x, sv)
        x = rearrange(x, "... h s e -> ... s (h e)")
        x = self.o_proj(x)
        return x

    def _forward_attn_varlen(
        self,
        x: Tensor, k: Tensor, v: Tensor,
        cu_q: Tensor, cu_seq: Tensor, max_q: int, max_seq: int
    ) -> Tensor:
        shape = x.shape
        #sv = rearrange(x.detach(), "... (h e) -> (...) h e", e=self.head_dim)

        x = self._forward_q(x, "(... s) h")
        x = cast(Tensor, varlen_attn(x, k, v, cu_q, cu_seq, max_q, max_seq))
        #x = self._xsa(x, sv)
        x = x.view(shape)
        x = self.o_proj(x)
        return x

    def forward(self, x: Tensor, k: Tensor, v: Tensor, attn_mask: Tensor | None) -> Tensor:
        x = x + self._forward_attn(x, k, v, attn_mask)
        x = x + self.ff(x)
        return x

    def forward_varlen(
        self,
        x: Tensor, k: Tensor, v: Tensor,
        cu_q: Tensor, cu_seq: Tensor, max_q: int, max_seq: int
    ) -> Tensor:
        x = x + self._forward_attn_varlen(x, k, v, cu_q, cu_seq, max_q, max_seq)
        x = x + self.ff(x)
        return x

    @staticmethod
    def _xsa(x: Tensor, sv: Tensor) -> Tensor:
        sv = normalize(sv, dim=-1, eps=1e-5)
        return x - torch.linalg.vecdot(x, sv).unsqueeze(-1) * sv

class HydraPool(Module):
    def __init__(
        self,
        n_classes: int,
        attn_dim: int,
        head_dim: int,
        *,
        mid_blocks: int = 0,
        input_dim: int = -1,
        ff_dim: int = -1,
        ff_dropout: float = 0.0,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        if input_dim < 0:
            input_dim = attn_dim

        if ff_dim < 0:
            ff_dim = attn_dim * 3

        assert attn_dim % head_dim == 0
        n_heads = attn_dim // head_dim

        self.head_dim = head_dim
        self.output_dim = attn_dim

        ff_glu: type[GLU]
        if mid_blocks == 0:
            ff_affine = True
            ff_glu = SwiGLU
        else:
            ff_affine = False
            ff_glu = SpGLU

        self.q = Parameter(torch.randn(
            n_heads, n_classes, head_dim,
            device=device, dtype=dtype
        ))
        setattr(self.q, "rr_clsdim", 1)

        self.kv = Linear(
            input_dim, attn_dim * 2, bias=False,
            device=device, dtype=dtype
        )
        setattr(self.kv.weight, "rr_muon_chunks", (2, n_heads))

        self.qk_norm = RMSNorm(
            head_dim, eps=1e-5, elementwise_affine=False
        )

        self.ff = _FeedForward(
            attn_dim, ff_dim,
            glu=ff_glu,
            affine=ff_affine,
            dropout=ff_dropout,
            device=device, dtype=dtype,
        )

        self.mid_blocks = ModuleList(
            _MidBlock(
                n_classes, attn_dim, head_dim, ff_dim,
                glu=ff_glu,
                ff_dropout=ff_dropout,
                device=device, dtype=dtype
            ) for _ in range(mid_blocks)
        )

        with torch.no_grad():
            self.q.copy_(self.qk_norm(self.q))

    @property
    def n_classes(self) -> int:
        return self.q.size(1)

    @property
    def _mid_blocks(self) -> MutableSequence[_MidBlock]:
        return cast(MutableSequence[_MidBlock], self.mid_blocks)

    def _forward_kv(self, x: Tensor, order: str = "h s") -> tuple[Tensor, Tensor]:
        x = self.kv(x)
        x, v = rearrange(x, f"... s (n h e) -> n ... {order} e", n=2, e=self.head_dim).unbind(0)
        x = self.qk_norm(x)
        return x, v

    def _forward_attn(self, x: Tensor, attn_mask: Tensor | None) -> tuple[Tensor, Tensor, Tensor]:
        q = self.q.expand(*x.shape[:-2], -1, -1, -1)
        k, v = self._forward_kv(x)

        x = scaled_dot_product_attention(q, k, v, attn_mask=attn_mask)
        return rearrange(x, "... h s e -> ... s (h e)"), k, v

    def _forward_attn_varlen(self, x: Tensor, cu_q: Tensor, cu_seq: Tensor, max_seq: int) -> tuple[Tensor, Tensor, Tensor]:
        q = self.q.transpose(0, 1).repeat_interleave(cu_q.size(0) - 1, 0)
        k, v = self._forward_kv(x, "s h")

        x = cast(Tensor, varlen_attn(q, k, v, cu_q, cu_seq, self.n_classes, max_seq))
        return rearrange(x, "(n s) h e -> n s (h e)", s=self.n_classes), k, v

    def forward(self, x: Tensor, attn_mask: Tensor | None = None) -> Tensor:
        x, k, v = self._forward_attn(x, attn_mask)
        x = x + self.ff(x)

        for block in self.mid_blocks:
            x = block(x, k, v, attn_mask)

        return x

    def forward_varlen(self, x: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        cu_q = torch.arange(
            0, cu_seq.size(0) * self.n_classes, self.n_classes,
            device=self.q.device, dtype=torch.int32
        )

        x, k, v = self._forward_attn_varlen(x, cu_q, cu_seq, max_seq)
        x = x + self.ff(x)

        for block in self._mid_blocks:
            x = block.forward_varlen(x, k, v, cu_q, cu_seq, self.n_classes, max_seq)

        return x

    def forward_unpooled(self, x: Tensor, attn_mask: Tensor | None = None) -> Tensor:
        k, v = self._forward_kv(x)

        x = rearrange(v, "... h s e -> ... s (h e)")
        x = x + self.ff(x)

        for block in self.mid_blocks:
            x = block(x, k, v, attn_mask)

        return x

    def forward_unpooled_varlen(self, x: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        k, v = self._forward_kv(x, "s h")

        x = rearrange(v, "s h e -> s (h e)")
        x = x + self.ff(x)

        for block in self._mid_blocks:
            x = block.forward_varlen(x, k, v, cu_seq, cu_seq, max_seq, max_seq)

        return x

    @classmethod
    def for_state(
        cls,
        state_dict: dict[str, Any],
        prefix: str = "",
        *,
        num_classes: int | None = None,
        ff_dropout: float = 0.0,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> Self:
        n_heads, n_classes, head_dim = state_dict[f"{prefix}q"].shape
        if num_classes is not None:
            n_classes = num_classes

        attn_dim = n_heads * head_dim

        input_dim = state_dict[f"{prefix}kv.weight"].size(1)
        ff_dim = state_dict[f"{prefix}ff.proj_out.weight"].size(1)

        pattern = re.compile(rf"^{re.escape(prefix)}mid_blocks\.([0-9]+)\.")
        mid_blocks = max([-1, *(
            int(match[1])
            for key in state_dict
            if (match := pattern.match(key)) is not None
        )]) + 1

        return cls(
            n_classes,
            attn_dim,
            head_dim,
            mid_blocks=mid_blocks,
            ff_dim=ff_dim,
            ff_dropout=ff_dropout,
            input_dim=input_dim,
            device=device,
            dtype=dtype
        )
