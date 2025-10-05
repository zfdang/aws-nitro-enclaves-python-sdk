"""Lightweight typed shim around the CFFI native extension.

This module exposes small helper functions so higher-level code can rely on
well-typed conversions (buffer -> bytes, pointer -> str) instead of casting
`Any` throughout the codebase.
"""
from __future__ import annotations

from typing import Any, cast

_native_ext: Any = None
try:  # pragma: no cover - exercised indirectly in tests
    from . import _native as _native_ext
except ImportError:  # pragma: no cover - handled in tests via monkeypatch
    _native_ext = None


# Expose untyped names — these are intentionally Any so callers don't have to
# repeatedly cast values coming from CFFI.
ffi: Any = getattr(_native_ext, "ffi", None)
lib: Any = getattr(_native_ext, "lib", None)


def ensure_native_available() -> None:
    if _native_ext is None:
        raise ImportError("CFFI extension aws_nitro_enclaves.nsm._native is not available")


def buf_to_bytes(buffer: Any, length: int) -> bytes:
    """Convert a CFFI buffer to bytes.

    The function raises when the native extension is missing; at runtime the
    underlying ffi.buffer(...) call returns a bytes-like object which we
    convert to bytes.
    """
    if ffi is None:
        raise ImportError("CFFI extension not available")
    return bytes(ffi.buffer(buffer, length))


def ptr_to_str(pointer: Any) -> str:
    """Convert a CFFI char* pointer to a Python str (ascii)."""
    if ffi is None:
        raise ImportError("CFFI extension not available")
    # ffi.string(...) is untyped; decode(...) returns Any to mypy — cast to
    # str so callers see a proper type.
    return cast(str, ffi.string(pointer).decode("ascii"))
