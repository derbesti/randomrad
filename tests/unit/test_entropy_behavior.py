import os
import pytest
import randomrad as rr
from randomrad.entropy import NotEnoughEntropy


def test_entropy_can_raise_when_blocking_disabled(tmp_path):
    """
    Demonstrates the intended behavior:
    - if blocking is disabled
    - and the entropy file runs out
    -> NotEnoughEntropy should be raised (no silent fallback).
    """
    tiny = tmp_path / "tiny.bin"
    tiny.write_bytes(b"\x00\x01\x02\x03")  # only 4 bytes

    os.environ["RANDOMRAD_BACKEND"] = "file"
    os.environ["RANDOMRAD_ENTROPY_FILE"] = str(tiny)
    os.environ["RANDOMRAD_FILE_LOOP"] = "0"
    os.environ["RANDOMRAD_BLOCK"] = "0"

    # First call can succeed (consumes some bytes)
    rr.randbytes(4)

    # Then it should fail immediately (no blocking, no loop)
    with pytest.raises(NotEnoughEntropy):
        rr.randbytes(16)