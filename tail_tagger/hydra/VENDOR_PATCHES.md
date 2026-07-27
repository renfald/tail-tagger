# Vendored Hydra — local patches

This package is a vendored copy of RedRocket's Hydra `hydra/` package
(source: https://huggingface.co/RedRocket/Hydra). The files here carry three local
divergences from upstream. **Re-apply them whenever Hydra is updated.**

To update: fetch a fresh upstream `hydra/` into a temporary location, then diff it
against this package to see what needs re-applying:

```bash
diff -ru path/to/fresh/hydra tail_tagger/hydra
```

Everything below should show up in that diff (plus the added `_compat.py`, which
upstream does not have).

---

## 1. Python 3.10 typing backport

Upstream imports `typing.Self` and `typing.NotRequired`, which are 3.11+. The app
supports 3.10, so those names are routed through `tail_tagger/hydra/_compat.py`,
which falls back to `typing_extensions` (declared in `requirements.txt` for
`python_version < "3.11"`).

- **Added file:** `_compat.py` — re-exports `Self` and `NotRequired`.
- **Changed imports** (from `typing` → `from ._compat`):
  - `model.py`, `label.py`, `pool.py`, `cufork.py` — `Self`
  - `siglip2.py` — `NotRequired`

## 2. PEP 646 starred-subscript syntax (3.10)

`siglip2.py` `NaFlexEmbeds._unpad` used starred subscript indexing
(`sizes[*idxs]`, `patches[*idxs, :seqlen]`), which is 3.11+ syntax and is a hard
`SyntaxError` on 3.10 (fails at import/compile, not runtime). Rewritten to explicit
tuple indexing:

- `sizes[*idxs]` → `sizes[idxs]`
- `patches[*idxs, :seqlen]` → `patches[idxs + (slice(None, seqlen),)]`
- `valid[*idxs, seqlen:]` → `valid[idxs + (slice(seqlen, None),)]`

See `siglip2.py` `_unpad` (~lines 136–143). Semantically identical; `idxs` is
already a tuple from `itertools.product`.

## 3. GLU activation descriptor-binding fix (`glu.py`)

`GLU._activation` is a `@staticmethod`. The `SwiGLU` / `SpGLU` subclasses override
it by assigning a bare function (`_activation = silu`). A bare function assigned as
a class attribute is a descriptor, so `self._activation(x)` binds `self` and calls
`activation(self, x)` — passing the module in as the tensor argument.

This bites `silu` (a Python function, hence a descriptor) and breaks the JTP-3
SwiGLU path; `softplus` happens to be a C builtin (not a descriptor), so the 3.5
SpGLU path works by luck. This is a latent upstream bug — their JTP-3 path would
break too; it just hasn't been exercised. `torch.compile` does not mask it.

**Fix:** wrap both in `staticmethod(...)` to restore the base class's intent:

```python
_activation = staticmethod(silu)     # SwiGLU
_activation = staticmethod(softplus) # SpGLU
```

See `glu.py` (~lines 72, 75) and the in-file comment above them for the full
rationale.
