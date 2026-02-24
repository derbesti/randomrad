"""
RANDU: historically bad linear congruential generator.

Formula (classic RANDU):
  X_{n+1} = (a * X_n) mod m
  a = 65539
  m = 2^31

We expose:
- next_state(state) -> (new_state, value)
- randbytes(n, seed=1) -> bytes

This is ONLY for comparison in analysis scripts.
"""

from __future__ import annotations

from typing import Tuple

A = 65539
M = 2 ** 31


def next_state(state: int) -> Tuple[int, int]:
    if state <= 0:
        # classic RANDU uses a non-zero seed; keep it simple
        state = 1
    state = (A * state) % M
    return state, state


def randbytes(n: int, seed: int = 1) -> bytes:
    if n < 0:
        raise ValueError("n must be >= 0")
    out = bytearray()
    state = seed
    for _ in range(n):
        state, x = next_state(state)
        out.append(x & 0xFF)  # use lowest 8 bits (shows weaknesses clearly)
    return bytes(out)