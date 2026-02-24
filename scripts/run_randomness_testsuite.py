"""
Run stevenang/randomness_testsuite (Python NIST-style tests) on a bitstream.

Upstream repo is included as a git submodule:
  _vendor/randomness_testsuite

Important: upstream is class-based, e.g.
  FrequencyTest.FrequencyTest().monobit_test(binary_data)

This script:
- generates a bitstring from randomrad (source=rr)
- runs a curated set of tests
- prints p-values + pass/fail
- optionally writes a JSON report

Usage:
  python scripts/run_randomness_testsuite.py --source rr --bits 8192
  python scripts/run_randomness_testsuite.py --source rr --bits 8192 --json docs/randomness_tests/rr_8192.json

Hardware later (PowerShell):
  $env:RANDOMRAD_BACKEND="hw"
  $env:RANDOMRAD_PORT="COM3"
  python scripts/run_randomness_testsuite.py --source rr --bits 1000000 --json docs/randomness_tests/hw_1M.json
"""

from __future__ import annotations

import argparse
import json
import sys
import importlib.resources as resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Ensure project root is on sys.path so we can import badprng when
# running this script via: python scripts/...
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import randomrad as rr




def _ensure_testsuite_on_path() -> None:
    """
    Make the vendored randomness_testsuite importable.

    Upstream uses flat, top-level imports like:
        from BinaryMatrix import BinaryMatrix

    Therefore we must add the directory containing those modules
    to sys.path (even though it is vendored inside our package).
    """
    try:
        # randomrad/_vendor/randomness_testsuite (as a package resource)
        pkg = "randomrad._vendor.randomness_testsuite"
        suite_dir = resources.files(pkg)
    except Exception as e:
        raise SystemExit(
            "Vendored randomness_testsuite not found in package.\n"
            "Expected: randomrad/_vendor/randomness_testsuite\n"
        ) from e

    sys.path.insert(0, str(suite_dir))


def _bytes_to_bitstring(data: bytes, nbits: int) -> str:
    """
    Convert bytes to '0'/'1' bitstring, MSB-first per byte. Truncate to nbits.
    """
    bits: list[str] = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append("1" if ((b >> i) & 1) else "0")
            if len(bits) >= nbits:
                return "".join(bits)
    return "".join(bits[:nbits])


def _make_bits_rr(nbits: int) -> str:
    nbytes = (nbits + 7) // 8
    data = rr.randbytes(nbytes)
    return _bytes_to_bitstring(data, nbits)

def _make_bits_randu(nbits: int) -> str:
    from badprng.randu import randbytes as randu_randbytes

    nbytes = (nbits + 7) // 8
    data = randu_randbytes(nbytes, seed=1)
    return _bytes_to_bitstring(data, nbits)

def _to_json_scalar(x: Any) -> Any:
    """
    Convert numpy scalars (numpy.float64, numpy.bool_, ...) into plain Python types.
    Leaves normal Python types unchanged.
    """
    if x is None:
        return None
    try:
        # numpy scalars implement .item()
        if hasattr(x, "item"):
            return x.item()
    except Exception:
        pass
    return x


@dataclass
class TestResult:
    name: str
    p_value: Any
    passed: Any


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["rr", "randu"], required=True)
    ap.add_argument("--bits", type=int, default=8192, help="Number of bits (>= 8192 recommended)")
    ap.add_argument("--json", default=None, help="Optional JSON output path")
    args = ap.parse_args()

    if args.bits <= 0:
        raise SystemExit("--bits must be > 0")

    _ensure_testsuite_on_path()

    import FrequencyTest
    import RunTest
    import Serial
    import Spectral
    import TemplateMatching
    import Universal
    import Complexity
    import ApproximateEntropy
    import CumulativeSum
    import Matrix

    freq = FrequencyTest.FrequencyTest()
    runs = RunTest.RunTest()
    serial = Serial.Serial()
    spectral = Spectral.SpectralTest()
    templ = TemplateMatching.TemplateMatching()
    univ = Universal.Universal()
    compl = Complexity.ComplexityTest()
    apen = ApproximateEntropy.ApproximateEntropy()
    csum = CumulativeSum.CumulativeSums()
    matrix = Matrix.Matrix()

    if args.source == "rr":
        bits = _make_bits_rr(args.bits)
    else:
        bits = _make_bits_randu(args.bits)

    # Most upstream methods return (p_value, passed_bool). We normalize those.
    funcs: list[tuple[str, Callable[[], Any]]] = [
        ("FrequencyTest.monobit_test", lambda: freq.monobit_test(bits)),
        ("FrequencyTest.block_frequency", lambda: freq.block_frequency(bits)),
        ("RunTest.run_test", lambda: runs.run_test(bits)),
        ("RunTest.longest_one_block_test", lambda: runs.longest_one_block_test(bits)),
        ("Matrix.binary_matrix_rank_text", lambda: matrix.binary_matrix_rank_text(bits)),
        ("SpectralTest.spectral_test", lambda: spectral.spectral_test(bits)),
        ("TemplateMatching.non_overlapping_test", lambda: templ.non_overlapping_test(bits)),
        ("TemplateMatching.overlapping_patterns", lambda: templ.overlapping_patterns(bits)),
        ("Universal.statistical_test", lambda: univ.statistical_test(bits)),
        ("ComplexityTest.linear_complexity_test", lambda: compl.linear_complexity_test(bits)),
        # Serial returns a tuple/list of two results; each looks like (p, pass)
        ("Serial.serial_test[0]", lambda: serial.serial_test(bits)[0]),
        ("Serial.serial_test[1]", lambda: serial.serial_test(bits)[1]),
        ("ApproximateEntropy.approximate_entropy_test", lambda: apen.approximate_entropy_test(bits)),
        ("CumulativeSums.forward", lambda: csum.cumulative_sums_test(bits, 0)),
        ("CumulativeSums.backward", lambda: csum.cumulative_sums_test(bits, 1)),
    ]

    results: list[TestResult] = []
    passed_count = 0

    print(f"Source={args.source} bits={args.bits}")
    for name, f in funcs:
        try:
            out = f()
        except Exception as e:
            results.append(TestResult(name=name, p_value=None, passed=False))
            print(f"{name}: ERROR {e}")
            continue

        # Parse output
        if isinstance(out, (tuple, list)) and len(out) >= 2:
            p_value, passed = out[0], out[1]
        else:
            p_value = out
            try:
                passed = bool(p_value >= 0.01)
            except Exception:
                passed = None

        # Normalize numpy scalars -> python types (JSON-safe)
        p_value = _to_json_scalar(p_value)
        passed = _to_json_scalar(passed)

        # Upstream sometimes uses -1.0 to indicate "not applicable / not enough data"
        if p_value == -1.0:
            passed = None

        # Ensure passed is a real bool when possible
        if passed is not None:
            passed = bool(passed)

        results.append(TestResult(name=name, p_value=p_value, passed=passed))

        if passed is True:
            passed_count += 1

        print(f"{name}: p={p_value} pass={passed}")

    summary = {
        "source": args.source,
        "bits": args.bits,
        "passed": passed_count,
        "total": len(results),
        "results": [r.__dict__ for r in results],
    }

    print(f"Passed {passed_count}/{len(results)} tests")

    if args.json:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(summary, fp, indent=2)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()