"""
Dump a bitstream from randomrad into a binary file.

Why:
- External test tools (NIST STS, dieharder, TestU01, etc.) consume bitstreams.
- This script exports raw bytes from randomrad.randbytes().

Important:
- Output is BINARY (raw bytes), not ASCII "0/1".
- The number of bytes written is ceil(bits/8).

Usage:
  python scripts/dump_bitstream.py --bits 1000000 --out rr_1M.bin

Hardware later:
  PowerShell:
    $env:RANDOMRAD_BACKEND="hw"
    $env:RANDOMRAD_PORT="COM3"
    python scripts/dump_bitstream.py --bits 10000000 --out hw_10M.bin
"""

from __future__ import annotations

import argparse

import randomrad as rr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, required=True, help="Number of bits to export (> 0)")
    ap.add_argument("--out", required=True, help="Output file path (binary)")
    args = ap.parse_args()

    if args.bits <= 0:
        raise SystemExit("--bits must be > 0")

    nbytes = (args.bits + 7) // 8

    # Pull bytes from randomrad. The backend is selected by env vars.
    data = rr.randbytes(nbytes)

    with open(args.out, "wb") as f:
        f.write(data)

    print(f"Wrote {nbytes} bytes (~{args.bits} bits) to {args.out}")


if __name__ == "__main__":
    main()