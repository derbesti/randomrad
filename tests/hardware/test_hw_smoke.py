"""
Hardware smoke tests.

These tests are intentionally tiny:
- they only verify that the hardware backend can deliver bytes
- and that the public API works end-to-end with REAL hardware entropy.

They are skipped unless you explicitly configure:
- RANDOMRAD_BACKEND=hw
- RANDOMRAD_PORT=<COM3 or /dev/ttyACM0>

Later, when the MicroPython device is connected and hw_backend.py is enabled
(pyserial code uncommented), you run:

Windows (PowerShell):
  $env:RANDOMRAD_BACKEND="hw"
  $env:RANDOMRAD_PORT="COM3"
  python -m pytest -m hardware

Linux/macOS:
  RANDOMRAD_BACKEND=hw RANDOMRAD_PORT=/dev/ttyACM0 python -m pytest -m hardware
"""

import os
import pytest

pytestmark = pytest.mark.hardware


def _hw_ready() -> bool:
    return os.environ.get("RANDOMRAD_BACKEND") == "hw" and bool(os.environ.get("RANDOMRAD_PORT"))


@pytest.mark.skipif(not _hw_ready(), reason="Hardware not configured (set RANDOMRAD_BACKEND=hw and RANDOMRAD_PORT).")
def test_hw_randbytes_32():
    import randomrad as rr
    b = rr.randbytes(32)
    assert isinstance(b, (bytes, bytearray))
    assert len(b) == 32


@pytest.mark.skipif(not _hw_ready(), reason="Hardware not configured (set RANDOMRAD_BACKEND=hw and RANDOMRAD_PORT).")
def test_hw_randint_range():
    import randomrad as rr
    x = rr.randint(0, 100)
    assert 0 <= x <= 100