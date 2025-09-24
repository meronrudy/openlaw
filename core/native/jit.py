"""
JIT Utilities for Native Reasoner

Provides safe wrappers around numba.njit so native components can opt-in to JIT
acceleration without introducing a hard dependency on numba at import time.

Usage:
    from core.native.jit import njit_if

    @njit_if(enable=True)
    def hot_loop(...):
        ...

Or dynamically:
    from core.native.jit import get_njit

    nj = get_njit(enable_jit_flag)
    @nj
    def fn(...):
        ...
"""

from __future__ import annotations
from typing import Callable, TypeVar, Any

F = TypeVar("F", bound=Callable[..., Any])


def _identity_decorator(fn: F) -> F:
    return fn


def get_njit(enable: bool = False) -> Callable[[F], F]:
    """
    Return a decorator that applies numba.njit when enable is True and numba is available,
    otherwise returns an identity decorator.

    Args:
        enable: Whether to attempt JIT compilation.

    Returns:
        A decorator usable as @decorator on functions.
    """
    if not enable:
        return _identity_decorator

    try:
        import numba  # type: ignore

        return numba.njit  # type: ignore[attr-defined]
    except Exception:
        return _identity_decorator


def njit_if(enable: bool = False) -> Callable[[F], F]:
    """
    Syntactic sugar over get_njit(enable) to be used as @njit_if(enable=flag).
    """
    return get_njit(enable)