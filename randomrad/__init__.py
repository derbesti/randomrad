"""
randomrad package public API.

This project exposes a small subset of Python's `random` API, but all randomness
comes from an entropy backend (file now, MicroPython hardware later).

No seed. No PRNG fallback.
"""

#pull selected names to top-level package
#. means import from the current package randomrad (relative import)
from .exceptions import RandomradError, NotEnoughEntropy, BackendError
from .entropy import get_bytes,use_backend, clear_backend_override, backend, current_backend
from .api import (
    random,
    randbytes,
    randrange,
    randint,
    choice,
    choices,
    shuffle,
    sample,
)

#takes from randomrad import *
__all__ = [
    "NotEnoughEntropy",
    "get_bytes",
    "random",
    "randbytes",
    "randrange",
    "randint",
    "choice",
    "choices",
    "shuffle",
    "sample",
    "NotEnoughEntropy",
    "get_bytes",
    "use_backend",
    "clear_backend_override",
    "backend",
    "current_backend"
]