"""
Test behaviour to prevent:
small entropy.bin + loop aktic + big read -> no crash
"""

import os
from pathlib import Path
import randomrad as rr

def test_file_backend_loop_allows_large_reads(tmp_path: Path, monkeypatch):
    # create tiny entropy file
    p = tmp_path / "entropy.bin"
    p.write_bytes(b"abcd")  # 4 bytes

    #monkeypatch set environment variables for the test run, doesnt change the system
    monkeypatch.setenv("RANDOMRAD_BACKEND", "file")
    monkeypatch.setenv("RANDOMRAD_ENTROPY_FILE", str(p))
    monkeypatch.setenv("RANDOMRAD_FILE_LOOP", "1")
    monkeypatch.setenv("RANDOMRAD_BLOCK", "0")

    rr.clear_backend_override()  # ensure env is used

    data = rr.randbytes(1000)
    assert len(data) == 1000
    # it must repeat the pattern
    assert data[:8] == b"abcdabcd"