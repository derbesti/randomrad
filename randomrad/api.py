"""
randomrad.api

Implements a small, random-like API ONLY using entropy bytes from randomrad.entropy.

Important constraints:
- No fallback to Python's random
- No seed / reproducibility mode
- All randomness comes from entropy.get_bytes(...)
"""

from __future__ import annotations

from collections.abc import MutableSequence, Sequence
from typing import TypeVar

#everything is built on top of:
from .entropy import get_bytes

#generic type variable
#used for static type checking only
#zero effect at runtime
#def choice(seq: Sequence[T]) -> T:
#“If you give me a sequence of X, I return an X.”
#T allows the function to preserve type information
T = TypeVar("T")

# -------------------------
# Core bit / integer helpers
# -------------------------


def randbytes(n: int) -> bytes:
    """Return n raw bytes from the configured entropy backend."""
    return get_bytes(n)


def _getrandbits(k: int) -> int:
    """
    Internal helper: return an integer with exactly k random bits.

    Implementation:
    - request ceil(k/8) bytes
    - convert to int
    - shift away extra bits (if k not multiple of 8)
    """
    if k < 0:
        raise ValueError("k must be >= 0")
    if k == 0:
        return 0

    nbytes = (k + 7) // 8
    x = int.from_bytes(get_bytes(nbytes), "big", signed=False)

    extra = (nbytes * 8) - k
    if extra:
        x >>= extra
    return x


def _randbelow(n: int) -> int:
    """
    Return a random integer in [0, n) without modulo bias
    using rejection sampling.
    """
    if n <= 0:
        raise ValueError("n must be > 0")

    k = n.bit_length()
    while True:
        r = _getrandbits(k)
        if r < n:
            return r


# -------------------------
# Public API (spec subset)
# -------------------------

def random() -> float:
    """
    Return float in [0.0, 1.0).

    Uses 53 random bits to match IEEE-754 double mantissa precision.
    """
    return _getrandbits(53) / (1 << 53)


def randrange(start: int, stop: int | None = None, step: int = 1) -> int:
    """
    Like random.randrange:
    - randrange(stop)
    - randrange(start, stop[, step])

    Note: step must not be 0.
    """
    if stop is None:
        stop = start
        start = 0

    if step == 0:
        raise ValueError("step must not be 0")

    if step > 0:
        if start >= stop:
            raise ValueError("empty range for randrange()")
        count = (stop - start + step - 1) // step
        return start + _randbelow(count) * step

    # step < 0
    if start <= stop:
        raise ValueError("empty range for randrange()")
    step_abs = -step
    count = (start - stop + step_abs - 1) // step_abs
    return start + _randbelow(count) * step  # step is negative


def randint(a: int, b: int) -> int:
    """Return random integer N such that a <= N <= b."""
    if a > b:
        raise ValueError("a must be <= b")
    return a + _randbelow(b - a + 1)


def choice(seq: Sequence[T]) -> T:
    """Return one random element from a non-empty sequence."""
    if len(seq) == 0:
        raise IndexError("Cannot choose from an empty sequence")
    return seq[_randbelow(len(seq))]


def choices(population: Sequence[T], k: int = 1) -> list[T]:
    """
    Return k elements drawn WITH replacement (order matters).

    Spec variant: only supports (population, k=1).
    """
    if k < 0:
        raise ValueError("k must be >= 0")
    if len(population) == 0 and k > 0:
        raise IndexError("Cannot choose from an empty population")
    return [population[_randbelow(len(population))] for _ in range(k)]


def shuffle(x: MutableSequence[T]) -> None:
    """
    Shuffle a mutable sequence in-place (Fisher-Yates).
    """
    for i in range(len(x) - 1, 0, -1):
        j = _randbelow(i + 1)
        x[i], x[j] = x[j], x[i]


def sample(population: Sequence[T], k: int = 1) -> list[T]:
    """
    Return k UNIQUE elements drawn WITHOUT replacement (order matters).

    Spec variant: supports (population, k=1).
    """
    n = len(population)
    if k < 0 or k > n:
        raise ValueError("sample larger than population or is negative")

    idx = list(range(n))
    # Partial Fisher-Yates shuffle for first k positions
    for i in range(k):
        j = i + _randbelow(n - i)
        idx[i], idx[j] = idx[j], idx[i]
    return [population[i] for i in idx[:k]]