from math import sqrt
from typing import Callable, ClassVar

import torch
from torch import Tensor
from torch.nn import Module, Parameter
from torch.nn.functional import silu, softplus, dropout

__all__ = ("GLU", "SwiGLU", "SpGLU")

class GLU(Module):
    def __init__(
        self,
        in_features: int, out_features: int,
        *,
        dropout: float = 0.0,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__()

        self.dropout = dropout

        self.weight = Parameter(torch.empty(
            out_features * 2, in_features,
            device=device, dtype=dtype,
        ))
        setattr(self.weight, "rr_muon_chunks", 2)

        torch.nn.init.kaiming_uniform_(self.weight, a=sqrt(5))

    def forward(self, x: Tensor) -> Tensor:
        x = x @ self.weight.T
        x, x2 = x.chunk(2, dim=-1)
        x = self._activation(x)
        x = x * x2
        del x2

        if self.training and self.dropout != 0.0:
            x = dropout(x, self.dropout)

        return x

    @staticmethod
    def _activation(x: Tensor) -> Tensor:
        raise NotImplementedError

# NOTE (tail-tagger local patch): wrap the activations in staticmethod.
#
# The base GLU._activation is a @staticmethod, but the subclasses below override it
# with a *bare* function. A bare function stored as a class attribute is a
# descriptor, so `self._activation` binds it as an instance method and
# `self._activation(x)` actually calls `activation(self, x)` -- passing the module
# as the function's first argument.
#
# Whether that breaks depends entirely on what the activation *is*:
#   * `silu`     is a pure-Python function  -> IS a descriptor -> gets bound ->
#                `silu(self, x)` treats `x` as the `inplace` flag -> RuntimeError.
#   * `softplus` is a C builtin             -> NOT a descriptor -> never bound ->
#                `softplus(x)` is called correctly.
# (Verified against torch 2.8: type(silu)=function, type(softplus)=builtin. This is
# not eager-vs-compiled -- torch.compile fails identically; it is purely the
# descriptor-binding asymmetry between the two callables.)
#
# Why the upstream Hydra project doesn't need this fix, but we do:
#   * Hydra 3.5 -- the default model they ship and showcase -- uses SpGLU (softplus),
#     which is a builtin and so never triggers the binding bug.
#   * Only the *legacy* JTP-3 Hydra model uses SwiGLU (silu). We keep JTP-3 selectable
#     and run it eagerly, which is exactly the under-exercised path that trips it.
# staticmethod() restores the base class's intent and makes both call correctly.
class SwiGLU(GLU):
    _activation = staticmethod(silu) # type: ignore[assignment]

class SpGLU(GLU):
    _activation = staticmethod(softplus) # type: ignore[assignment]
