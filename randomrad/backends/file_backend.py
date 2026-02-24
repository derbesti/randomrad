"""
File backend (development / dummy hardware).

Reads raw bytes from a file (default: entropy/entropy.bin)

Env vars:
- RANDOMRAD_ENTROPY_FILE : path to file (default: entropy/entropy.bin)
- RANDOMRAD_FILE_LOOP    : "1" -> loop file like ring buffer (default)
                           "0" -> exhaust file, then NotEnoughEntropy

Design note:
- Path is resolved relative to the *project root* (one level above the
  randomrad package directory), so running from tests/ or scripts/ works.
"""

from __future__ import annotations

import os
from pathlib import Path


from randomrad.exceptions import NotEnoughEntropy

def _resolve_entropy_path(raw_path: str) -> str:
    """
    Resolve entropy file path.

    - If raw_path is absolute -> use it.
    - If raw_path is relative -> treat it as relative to PROJECT ROOT,
      not the current working directory.
    """
    p = Path(raw_path)
    if p.is_absolute():
        return str(p)

    # randomrad/backends/file_backend.py -> parents[2] = project root
    project_root = Path(__file__).resolve().parents[2]
    return str(project_root / p)


class _FileEntropySource:
    def __init__(self, path: str, loop: bool) -> None:
        self.path = path
        self.loop = loop
        # Keep file open to behave like a continuous stream
        try:
            self._f = open(path, "rb")
        except FileNotFoundError as e:
            raise NotEnoughEntropy(
                "Entropy file not found. "
                "Set RANDOMRAD_ENTROPY_FILE or create entropy.bin in current directory."
            ) from e

        # Guard: empty file would make looping impossible
        self._f.seek(0, 2)  # end
        size = self._f.tell()
        self._f.seek(0)
        if size == 0:
            raise NotEnoughEntropy(f"entropy file is empty: {self.path}")

    def close(self) -> None:
        try:
            self._f.close()
        except Exception:
            pass

    def read_exact(self, n: int) -> bytes:
        """
        read exactly n bytes from entropy file or raise NotEnoughEntropy
        :param n:
        :return:
        """
        chunks: list[bytes] = []
        remaining = n

        while remaining > 0:
            part = self._f.read(remaining)
            if part:
                chunks.append(part)
                remaining -= len(part)
                continue

            # End of File:
            #no loop
            if not self.loop:
                break

            #with loop
            self._f.seek(0)

        data = b"".join(chunks)

        #no partial reads
        if len(data) != n:
            raise NotEnoughEntropy(f"not enough entropy available (file exhausted): {self.path}")
        return data


# Singleton source to behave like a stream
# dont create a new file object per call
_SOURCE: _FileEntropySource | None = None
_SOURCE_CFG: tuple[str, bool] | None = None  # (resolved_path, loop)


def _source() -> _FileEntropySource:
    global _SOURCE, _SOURCE_CFG

    raw_path = os.environ.get("RANDOMRAD_ENTROPY_FILE", "entropy.bin")
    path = _resolve_entropy_path(raw_path)
    loop = os.environ.get("RANDOMRAD_FILE_LOOP", "1").strip() != "0"
    cfg = (path, loop)

    # Recreate source when config changes
    if _SOURCE is None or _SOURCE_CFG != cfg:
        if _SOURCE is not None:
            _SOURCE.close()
        _SOURCE = _FileEntropySource(path=path, loop=loop)
        _SOURCE_CFG = cfg

    return _SOURCE


def get_bytes(n: int) -> bytes:
    """Return exactly n bytes or raise NotEnoughEntropy."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if n == 0:
        return b""
    return _source().read_exact(n)