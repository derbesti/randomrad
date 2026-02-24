"""
One-shot randomness comparison report.

Runs:
  - randomrad (rr)
  - RANDU (badprng)

Generates:
  - JSON result files
  - Histogram images (rr + randu), BOTH:
      * unbiased (rejection-mapped) 1..100  [fair]
      * biased (byte % 100) mapping         [structure amplifier / demo]
  - Markdown comparison report referencing the images

Usage:
  python scripts/make_report.py --bits 8192
  python scripts/make_report.py --bits 1000000 --hist-n 100000 --out docs/randomness_tests/report_1M.md

Notes:
- Histogram uses N integer samples in [1, 100].
- For rr, samples come from randomrad byte stream.
- For randu, samples come from badprng RANDU byte stream.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime
import sys
from typing import Callable


# Ensure project root is on sys.path so we can import badprng and randomrad
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_tests(source: str, bits: int, json_path: Path) -> None:
    cmd = [
        "python",
        "scripts/run_randomness_testsuite.py",
        "--source",
        source,
        "--bits",
        str(bits),
        "--json",
        str(json_path),
    ]
    subprocess.run(cmd, check=True)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------
# Histogram mapping helpers
# -------------------------

def _map_1_100_biased(data: bytes) -> list[int]:
    """
    Fast but biased mapping:
      value = (byte % 100) + 1

    Bias source:
      256 is not divisible by 100, so values 1..56 occur slightly more often.
    """
    return [(b % 100) + 1 for b in data]


def _samples_1_100_unbiased(source_bytes_fn: Callable[[int], bytes], n: int, *, chunk: int = 4096) -> list[int]:
    """
    Unbiased mapping from bytes to 1..100 using rejection sampling.

    Accept a byte only if b < 200 (since 200 is divisible by 100).
    Then (b % 100) is uniform on 0..99, so (b % 100) + 1 is uniform on 1..100.

    This removes mapping bias completely.
    """
    out: list[int] = []
    while len(out) < n:
        data = source_bytes_fn(chunk)
        for b in data:
            if b < 200:
                out.append((b % 100) + 1)
                if len(out) >= n:
                    break
    return out


# -------------------------
# Histogram generation
# -------------------------

def save_histogram(source: str, n: int, out_png: Path, *, unbiased: bool) -> None:
    """
    Save histogram PNG for N samples in [1,100].

    unbiased=True:
      Uses rejection sampling (fair / no mapping bias).

    unbiased=False:
      Uses (byte % 100) mapping (biased, but good at amplifying structure).
    """
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        raise SystemExit(
            "matplotlib is required for histogram generation.\n"
            "Install it via:\n"
            "  python -m pip install -e \".[analysis]\"\n"
        ) from e

    if source == "rr":
        import randomrad as rr

        if unbiased:
            values = _samples_1_100_unbiased(rr.randbytes, n)
            title = f"Histogram randomrad (unbiased 1..100 via rejection) (n={n})"
        else:
            data = rr.randbytes(n)
            values = _map_1_100_biased(data)
            title = f"Histogram randomrad (biased byte%100 mapping) (n={n})"

    elif source == "randu":
        from badprng.randu import randbytes as randu_randbytes

        if unbiased:
            values = _samples_1_100_unbiased(lambda k: randu_randbytes(k, seed=1), n)
            title = f"Histogram RANDU (unbiased 1..100 via rejection) (n={n})"
        else:
            data = randu_randbytes(n, seed=1)
            values = _map_1_100_biased(data)
            title = f"Histogram RANDU (biased byte%100 mapping) (n={n})"

    else:
        raise ValueError("unknown source")

    plt.figure()
    plt.hist(values, bins=100)
    plt.title(title)
    plt.xlabel("value")
    plt.ylabel("count")
    plt.tight_layout()

    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()


# -------------------------
# Markdown report
# -------------------------

def make_markdown(
    rr: dict,
    randu: dict,
    bits: int,
    hist_rr_unbiased: str | None,
    hist_randu_unbiased: str | None,
    hist_rr_biased: str | None,
    hist_randu_biased: str | None,
    hist_n: int | None,
) -> str:
    lines: list[str] = []
    lines.append("# Randomness Comparison Report")
    lines.append("")
    lines.append(f"- Date: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Bits (testsuite): {bits}")
    if hist_n is not None:
        lines.append(f"- Histogram samples: {hist_n} (range 1..100)")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- randomrad passed: **{rr['passed']}/{rr['total']}**")
    lines.append(f"- RANDU passed: **{randu['passed']}/{randu['total']}**")
    lines.append("")

    # Unbiased (fair)
    if hist_rr_unbiased and hist_randu_unbiased:
        lines.append("## Histograms (Unbiased / Fair Mapping)")
        lines.append("")
        lines.append(
            "These histograms use rejection sampling to map bytes to 1..100 without modulo bias "
            "(accept only bytes < 200, then (b % 100) + 1)."
        )
        lines.append("")
        lines.append("### randomrad (unbiased)")
        lines.append(f"![rr histogram unbiased]({hist_rr_unbiased})")
        lines.append("")
        lines.append("### RANDU (unbiased)")
        lines.append(f"![randu histogram unbiased]({hist_randu_unbiased})")
        lines.append("")

    # Biased (structure amplifier)
    if hist_rr_biased and hist_randu_biased:
        lines.append("## Histograms (Biased Mapping / Structure Amplifier)")
        lines.append("")
        lines.append(
            "These histograms use the fast mapping (byte % 100) + 1. This is intentionally biased because "
            "256 is not divisible by 100, so values 1..56 occur slightly more often even for a perfect RNG. "
            "It can be useful as a quick 'structure amplifier' (especially for weak generators), but it is "
            "not a fair uniformity check."
        )
        lines.append("")
        lines.append("### randomrad (biased)")
        lines.append(f"![rr histogram biased]({hist_rr_biased})")
        lines.append("")
        lines.append("### RANDU (biased)")
        lines.append(f"![randu histogram biased]({hist_randu_biased})")
        lines.append("")

    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| Test | rr p-value | rr pass | randu p-value | randu pass |")
    lines.append("|------|------------|---------|---------------|------------|")

    rr_map = {r["name"]: r for r in rr["results"]}
    randu_map = {r["name"]: r for r in randu["results"]}

    for name in rr_map.keys():
        r1 = rr_map.get(name)
        r2 = randu_map.get(name)
        lines.append(
            f"| {name} "
            f"| {r1['p_value']} | {r1['passed']} "
            f"| {r2['p_value']} | {r2['passed']} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Tests with p-value < 0.01 are typically considered failures.\n"
        "A significantly lower pass count indicates weaker statistical quality.\n"
        "\n"
        "Histograms are only a quick 1D sanity check. They do not detect many\n"
        "forms of correlation or structure that the statistical tests can detect."
    )

    return "\n".join(lines)


# -------------------------
# Main
# -------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, default=8192)
    ap.add_argument(
        "--out",
        default=None,
        help="Markdown output path (default: docs/randomness_tests/report_<bits>.md)",
    )
    ap.add_argument(
        "--hist-n",
        type=int,
        default=100_000,
        help="Number of samples for histogram (set 0 to disable)",
    )
    args = ap.parse_args()

    bits = args.bits

    base_dir = Path("docs/randomness_tests")
    base_dir.mkdir(parents=True, exist_ok=True)

    rr_json = base_dir / f"rr_{bits}.json"
    randu_json = base_dir / f"randu_{bits}.json"

    print("Running randomrad...")
    run_tests("rr", bits, rr_json)

    print("Running RANDU...")
    run_tests("randu", bits, randu_json)

    rr_data = load_json(rr_json)
    randu_data = load_json(randu_json)

    # Histograms (optional)
    hist_rr_unbiased_rel = None
    hist_randu_unbiased_rel = None
    hist_rr_biased_rel = None
    hist_randu_biased_rel = None
    hist_n = None

    if args.hist_n and args.hist_n > 0:
        hist_n = args.hist_n

        hist_rr_unbiased = base_dir / f"hist_rr_unbiased_{hist_n}.png"
        hist_randu_unbiased = base_dir / f"hist_randu_unbiased_{hist_n}.png"
        hist_rr_biased = base_dir / f"hist_rr_biased_{hist_n}.png"
        hist_randu_biased = base_dir / f"hist_randu_biased_{hist_n}.png"

        print(f"Generating histograms (n={hist_n})...")

        # Fair comparison
        save_histogram("rr", hist_n, hist_rr_unbiased, unbiased=True)
        save_histogram("randu", hist_n, hist_randu_unbiased, unbiased=True)

        # Structure amplifier (biased)
        save_histogram("rr", hist_n, hist_rr_biased, unbiased=False)
        save_histogram("randu", hist_n, hist_randu_biased, unbiased=False)

        # Markdown links should be relative to the report location (same dir)
        hist_rr_unbiased_rel = hist_rr_unbiased.name
        hist_randu_unbiased_rel = hist_randu_unbiased.name
        hist_rr_biased_rel = hist_rr_biased.name
        hist_randu_biased_rel = hist_randu_biased.name

    md = make_markdown(
        rr_data,
        randu_data,
        bits,
        hist_rr_unbiased_rel,
        hist_randu_unbiased_rel,
        hist_rr_biased_rel,
        hist_randu_biased_rel,
        hist_n,
    )

    out_path = Path(args.out) if args.out else (base_dir / f"report_{bits}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()