"""
randomrad.entropy

Single entry point for entropy bytes.

Goals:
- Keep env var configuration (good for CLI, CI, production)
- Add a *runtime backend switch* for fast dev workflows (PyCharm):
    import randomrad as rr
    rr.use_backend("hw")   # or "file"
- Optional context manager:
    with rr.backend("hw"):
        ...
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Callable, Optional



from .exceptions import NotEnoughEntropy

# optional: SerialException nur wenn vorhanden
try:
    import serial  # type: ignore
    _SERIAL_EXC = (serial.SerialException,)  # noqa
except Exception:
    _SERIAL_EXC = tuple()


# --------------------------------------------------------------------------------------
# Backend selection: env + runtime override
# --------------------------------------------------------------------------------------

# Runtime override (if set, it wins over env var)
_RUNTIME_BACKEND: Optional[str] = None

# Cached backend getter (a function get_bytes(n)->bytes)
_BACKEND_GETTER: Optional[Callable[[int], bytes]] = None
_BACKEND_NAME_CACHED: Optional[str] = None


def _env_backend() -> str:
    # Default remains file to keep dev experience smooth
    return os.environ.get("RANDOMRAD_BACKEND", "file").strip().lower()


def current_backend() -> str:
    """Return the currently effective backend name ('file' or 'hw')."""
    return (_RUNTIME_BACKEND or _env_backend()).strip().lower()


def use_backend(name: str, *, port: str | None = None) -> None:
    """
    Switch backend at runtime.

    Example:
        rr.use_backend("hw", port="COM4")
        rr.use_backend("file")
    """
    global _RUNTIME_BACKEND
    name = name.strip().lower()
    if name not in ("file", "hw"):
        raise ValueError("Backend must be 'file' or 'hw'")

    if name == "hw" and port:
        os.environ["RANDOMRAD_PORT"] = port

    _RUNTIME_BACKEND = name
    _invalidate_backend_cache()


def clear_backend_override() -> None:
    """
    Remove runtime override so env var controls backend again.
    """
    global _RUNTIME_BACKEND
    _RUNTIME_BACKEND = None
    _invalidate_backend_cache()


@contextmanager
def backend(name: str):
    """
    Context manager to temporarily switch backends.

    Example:
        with rr.backend("hw"):
            rr.random()
    """
    global _RUNTIME_BACKEND

    prev = _RUNTIME_BACKEND
    use_backend(name)
    try:
        yield
    finally:
        _RUNTIME_BACKEND = prev
        _invalidate_backend_cache()


def _invalidate_backend_cache() -> None:
    global _BACKEND_GETTER, _BACKEND_NAME_CACHED
    _BACKEND_GETTER = None
    _BACKEND_NAME_CACHED = None


def _load_backend_getter(name: str) -> Callable[[int], bytes]:
    """
    Import the selected backend lazily and return its get_bytes function.
    """
    if name == "file":
        from randomrad.backends.file_backend import get_bytes as _get_bytes
        return _get_bytes
    if name == "hw":
        from randomrad.backends.hw_backend import get_bytes as _get_bytes
        return _get_bytes
    raise ValueError(f"Unknown backend: {name}")


def _get_backend_getter() -> Callable[[int], bytes]:
    """
    Return cached get_bytes function for current backend.
    Rebuild cache if backend changed (env or runtime switch).
    """
    global _BACKEND_GETTER, _BACKEND_NAME_CACHED

    name = current_backend()
    if _BACKEND_GETTER is None or _BACKEND_NAME_CACHED != name:
        _BACKEND_GETTER = _load_backend_getter(name)
        _BACKEND_NAME_CACHED = name
    return _BACKEND_GETTER


# --------------------------------------------------------------------------------------
# Blocking policy
# --------------------------------------------------------------------------------------

def _blocking_enabled() -> bool:
    # Default: block (matches your "waiting for entropy is ok" philosophy)
    return os.environ.get("RANDOMRAD_BLOCK", "1").strip() not in ("0", "false", "no")


def _timeout_seconds() -> Optional[float]:
    v = os.environ.get("RANDOMRAD_TIMEOUT_S", "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


_EXPECTED = (NotEnoughEntropy, OSError, *_SERIAL_EXC)

def get_bytes(n: int) -> bytes:
    if n < 0:
        raise ValueError("n must be >= 0")
    if n == 0:
        return b""

    block = _blocking_enabled()
    timeout_s = _timeout_seconds()  # None = infinite
    start = time.monotonic()

    while True:
        try:
            getter = _get_backend_getter()
            return getter(n)
        except _EXPECTED as e:
            if not block:
                raise NotEnoughEntropy(str(e)) from e

            if timeout_s is not None and (time.monotonic() - start) >= timeout_s:
                raise NotEnoughEntropy(str(e)) from e

            time.sleep(0.01)