"""
Generate a histogram for N random integers in [1, 100] using randomrad.

Why:
- quick visual sanity check (distribution / obvious bias)
- useful for report screenshots

Usage:
  python scripts/histogram_100k.py --out histogram_rr.png
  python scripts/histogram_100k.py --n 500000 --out histogram_rr_500k.png

Hardware later (PowerShell):
  $env:RANDOMRAD_BACKEND="hw"
  $env:RANDOMRAD_PORT="COM3"
  python scripts/histogram_100k.py --out histogram_hw.png
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import randomrad as rr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100_000, help="Number of samples")
    ap.add_argument("--out", required=True, help="Output PNG filename")
    args = ap.parse_args()

    if args.n <= 0:
        raise SystemExit("--n must be > 0")

    # Generate values 1..100 (inclusive)
    values = [rr.randint(1, 100) for _ in range(args.n)]

    # Plot histogram: 100 bins for values 1..100
    plt.figure()
    plt.hist(values, bins=100)
    plt.title(f"Histogram randomrad.randint(1,100) (n={args.n})")
    plt.xlabel("value")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(args.out)

    print(f"Saved histogram to {args.out}")


if __name__ == "__main__":
    main()