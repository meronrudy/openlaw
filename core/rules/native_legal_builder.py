"""
Compatibility shim (deprecated): core.rules.native_legal_builder

This legacy module path is deprecated and maintained only for backward compatibility.
All exports are forwarded to core.rules_native.native_legal_builder.

Use:
  from core.rules_native.native_legal_builder import ...

This shim will be removed in a future release.
"""
from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "core.rules.native_legal_builder is deprecated; "
    "use core.rules_native.native_legal_builder",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols from the canonical implementation
from core.rules_native.native_legal_builder import *  # noqa: F401,F403

# Preserve __all__ for tools relying on explicit export lists
try:
    from core.rules_native.native_legal_builder import __all__ as _all  # type: ignore
    __all__ = list(_all)
except Exception:  # pragma: no cover
    __all__ = []