from math import sqrt, log
from typing import Literal
from itertools import product

import torch
from torch import Tensor

from torch.masked import softmax as masked_softmax
from torch.nested import nested_tensor_from_jagged

from torch.nn import (
    Module, Parameter,
    LayerNorm, RMSNorm,
    init
)
from torch.nn.functional import normalize, silu

__all__ = ("LinearHead", "SwiGLUHead", "SSMPool")

class BatchLinear(Module):
    def __init__(
        self,
        batch_shape: tuple[int, ...] | int,
        in_features: int,
        out_features: int,
        *,
        bias: bool = False,
        bias_inplace: bool = True,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        if isinstance(batch_shape, int):
            batch_shape = (batch_shape,)
        elif not batch_shape:
            raise ValueError("At least one batch dimension is required.")

        self.weight = Parameter(torch.empty(
            *batch_shape, out_features, in_features,
            device=device, dtype=dtype
        ))

        for idxs in product(range(size) for size in batch_shape):
            init.kaiming_uniform_(self.weight[idxs], a=sqrt(5))

        self.bias = Parameter(torch.zeros(
            *batch_shape, out_features,
            device=device, dtype=dtype
        )) if bias else None

        self.bias_inplace = bias_inplace

    def forward(self, x: Tensor) -> Tensor:
        # ... B... 1 I @ B... I O -> ... B... O
        x = torch.matmul(x.unsqueeze(-2), self.weight.mT).squeeze(-2)

        if self.bias is not None:
            if self.bias_inplace:
                x.add_(self.bias)
            else:
                x = x + self.bias

        return x

class LinearHead(Module):
    def __init__(
        self,
        n_classes: int,
        input_dim: int,
        *,
        logit: bool = True,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.logit = logit

        self.weight = Parameter(torch.randn(
            n_classes, input_dim,
            device=device, dtype=dtype
        ))
        setattr(self.weight, "rr_clsdim", 0)

        with torch.no_grad():
            normalize(self.weight, out=self.weight)

    def forward(self, x: Tensor) -> Tensor:
        x = torch.linalg.vecdot(x, self.weight)

        if self.logit:
            return x

        x = x.float()
        return x.sigmoid()

class SwiGLUHead(Module):
    def __init__(
        self,
        n_classes: int,
        input_dim: int,
        *,
        logit: bool = True,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.logit = logit

        self.proj = BatchLinear(
            n_classes, input_dim, 2,
            device=device, dtype=dtype
        )
        setattr(self.proj.weight, "rr_clsdim", 0)

    def forward(self, x: Tensor) -> Tensor:
        x = self.proj(x)
        x, x2 = x.unbind(-1)

        x = silu(x) * x2
        del x2

        if self.logit:
            return x

        x = x.float()
        return x.sigmoid()

class ExtremumPool(Module):
    def forward(self, x: Tensor, valid: Tensor | None = None) -> Tensor:
        s = x.abs()

        if valid is None:
            s = s.softmax(-2)
        else:
            s = masked_softmax(s, dim=-2, mask=valid.unsqueeze(-1))

        return torch.linalg.vecdot(x, s, dim=-2)

    def forward_varlen(self, x: Tensor, cu_seq: Tensor, max_seq: int) -> Tensor:
        assert x.ndim == 2

        x = nested_tensor_from_jagged(x, cu_seq, max_seqlen=max_seq)
        s = x.abs().softmax(1)
        return torch.linalg.vecdot(x, s, dim=1)
