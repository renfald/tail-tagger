"""Typing backports for Python 3.10 support.

The vendored Hydra package uses ``typing.Self`` and ``typing.NotRequired``,
which were added in Python 3.11. On 3.10 we fall back to ``typing_extensions``
(declared in requirements.txt for ``python_version < "3.11"``). On 3.11+ these
come straight from the stdlib and ``typing_extensions`` is not required.
"""

try:  # Python 3.11+
    from typing import Self, NotRequired
except ImportError:  # Python 3.10
    from typing_extensions import Self, NotRequired

__all__ = ["Self", "NotRequired"]
