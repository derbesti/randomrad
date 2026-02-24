"""
pytest configuration.

We force the file backend for unit tests so that tests are deterministic
and do not require hardware.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _force_file_backend():
    # Ensure unit tests never accidentally use hardware
    os.environ["RANDOMRAD_BACKEND"] = "file"
    os.environ.setdefault("RANDOMRAD_ENTROPY_FILE", "entropy.bin")
    os.environ.setdefault("RANDOMRAD_FILE_LOOP", "1")
    os.environ.setdefault("RANDOMRAD_BLOCK", "1")