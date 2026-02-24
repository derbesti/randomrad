# randomrad

Hardware-backed randomness module with full statistical validation pipeline.

`randomrad` provides a subset of Python’s `random` API — but **all randomness originates from external entropy**, never from a pseudo-random generator (PRNG).

The project is built as a transparent entropy pipeline:

- External entropy source (file or ESP32)
- Deterministic development mode (file)
- Hardware streaming mode (ESP32 MicroPython over serial)
- Chunked serial transport for large requests
- SHA-256 whitening on-device
- Statistical validation (NIST-style tests)
- Automated reporting (histograms + Markdown)
- Negative control comparison (RANDU via `badprng`)

---

# 🚀 Quick Start (External Users)

## Install (PyPI-ready)

When published to PyPI, users can install with:

```bash
pip install randomrad
```

Optional features are installed via **extras**:

```bash
# Hardware backend (ESP32 serial)
pip install "randomrad[hw]"

# Statistical validation dependencies (NumPy/SciPy)
pip install "randomrad[stats]"

# Report generation (matplotlib)
pip install "randomrad[analysis]"

# Everything (hw + stats + analysis + dev)
pip install "randomrad[all]"
```

> Note: `randomrad` ships a vendored copy of the NIST-style test suite used by the validation scripts.

---

## Option A — Use File Backend (No Hardware Required)

### Step 1 — Create an entropy file

From project root:

```bash
mkdir -p entropy
python -c "import os; open('entropy/entropy.bin','wb').write(os.urandom(1024*1024))"
```

### Step 2 — Use in Python

```python
import randomrad as rr

rr.use_backend("file")

print(rr.randbytes(16))
print(rr.random())
print(rr.randint(0, 100))
```

---

## Option B — Use Hardware Backend (ESP32)

### Step 1 — Flash ESP32 with provided MicroPython server

The device must implement this protocol:

```
Host → "R n\n"
Device → "D n\n" + n raw bytes
```

(See `esp32/main.py` in this repository.)

### Step 2 — Install hardware dependency

```bash
pip install "randomrad[hw]"
```

### Step 3 — Use in Python

```python
import randomrad as rr

rr.use_backend("hw", port="COM4")

print(rr.random())
print(rr.randint(0, 100))
```

---

# ✅ API Overview

Functions provided:

- `randbytes(n)`
- `getrandbits(k)`
- `random()`
- `randint(a, b)` (uniform via rejection sampling)
- `choice(seq)`
- `choices(seq,k)`
- `shuffle(seq)`
- `sample(seq,k)`


---

# ⚙ Runtime Backend Switching

Switch dynamically in code:

```python
import randomrad as rr

rr.use_backend("file")
print("FILE:", rr.random())

rr.use_backend("hw", port="COM4")
print("HW:", rr.random())

with rr.backend("file"):
    print("TEMP FILE:", rr.random())

print("current:", rr.current_backend())
```

> Tip: In PyCharm, create two Run Configurations:
> - FILE: `RANDOMRAD_BACKEND=file`, `RANDOMRAD_BLOCK=0`
> - HW: `RANDOMRAD_BACKEND=hw`, `RANDOMRAD_PORT=COM4`, `RANDOMRAD_BLOCK=0`

---

# 🧠 How It Works (Technical Overview)

## Philosophy

Unlike Python’s built-in `random` module:

- ❌ No seed
- ❌ No recurrence formula
- ❌ No hidden fallback to `random`
- ✅ All entropy comes from a backend
- ✅ Entropy is consumed as a stream

Mathematically:

```
X = integer constructed directly from entropy bytes
random() = X / 2^53
```

There is no internal PRNG state.

---

## Architecture Diagram

```
ESP32 (MicroPython)
  - os.urandom()
  - timing jitter
  - optional ADC noise
  - SHA-256 whitening
        ↓
Serial protocol ("R n" / "D n")
        ↓
hw_backend.py
  - DTR/RTS disabled
  - Boot-noise resync
  - Chunking (default 2048 bytes)
        ↓
entropy.py
  - Backend abstraction
  - Runtime switch
  - Blocking / timeout logic
        ↓
api.py
  - randbytes
  - getrandbits
  - random()
  - randint() (rejection sampling)
        ↓
Validation Pipeline
  - NIST-style tests
  - Histogram reports
  - RANDU comparison
```

---

## Entropy Lifecycle

```
Physical Noise (ESP32)
        ↓
Raw entropy collection
        ↓
SHA-256 whitening
        ↓
Serial streaming (chunked)
        ↓
Host backend assembly
        ↓
API transformation
        ↓
Statistical validation
```

Key properties:

- Conditioning happens on device
- Chunking happens on host
- API is a pure transformation layer
- Validation closes the loop

---

# 🔌 Backends

## File backend

Default file:

```
entropy/entropy.bin
```

Properties:

- Path resolved relative to project root (independent of working directory)
- Optional loop mode (ring buffer)
- Deterministic when file and start position are identical

Environment variables:

| Variable | Meaning |
|----------|---------|
| `RANDOMRAD_BACKEND=file` | Activate file backend |
| `RANDOMRAD_ENTROPY_FILE` | Custom entropy file path |
| `RANDOMRAD_FILE_LOOP` | `1`=loop (default), `0`=exhaust |

---

## Hardware backend (ESP32)

Protocol:

```
Host → "R n\n"
Device → "D n\n" + n raw bytes
```

Properties:

- Automatic chunking for large requests
- Boot-noise resynchronization
- DTR/RTS disabled to avoid auto-reset
- Configurable timeout

Environment variables:

| Variable | Meaning |
|----------|---------|
| `RANDOMRAD_BACKEND=hw` | Activate hardware backend |
| `RANDOMRAD_PORT` | Serial port (e.g. `COM4`) |
| `RANDOMRAD_SERIAL_TIMEOUT` | Read timeout (seconds) |
| `RANDOMRAD_HW_MAX_CHUNK` | Max chunk size per request |
| `RANDOMRAD_BLOCK` | `1`=block (default), `0`=fail fast |

---

# ⏱ Blocking Behavior

Default: blocking enabled.

Disable blocking (recommended for dev):

```bash
set RANDOMRAD_BLOCK=0
```

Set a timeout:

```bash
set RANDOMRAD_TIMEOUT_S=2
```

Missing entropy file or missing hardware configuration raises `NotEnoughEntropy`.

---

# 📊 Statistical Validation

## Install dependencies

```bash
pip install "randomrad[stats,analysis]"
```

## Run NIST-style tests

Small run:

```bash
python scripts/run_randomness_testsuite.py --source rr --bits 8192 --json docs/randomness_tests/rr_8192.json
```

Large run (recommended):

```bash
python scripts/run_randomness_testsuite.py --source rr --bits 1000000 --json docs/randomness_tests/hw_1M.json
```

> In hardware mode, ensure `RANDOMRAD_BACKEND=hw` and `RANDOMRAD_PORT=COM4` are set.

---

## Generate a full report (histograms + Markdown)

```bash
python scripts/make_report.py --bits 1000000 --hist-n 100000 --out docs/randomness_tests/report_hw_1M.md
```

Outputs:

- JSON result files (p-values, pass/fail)
- Histogram PNG images
- Markdown report (includes a summary table)

Histogram generation is optimized for hardware by pulling bytes in bulk.

---

# 🧪 Testing

Install dev dependencies:

```bash
pip install "randomrad[dev]"
```

Run all tests:

```bash
python -m pytest
```

Hardware-only tests:

```bash
python -m pytest -m hardware
```

---

# 🎯 Design Goals

- Clear separation of layers
- No hidden PRNG fallback
- Deterministic development mode
- Reliable hardware streaming
- Full statistical transparency

---

# 🚫 What This Project Is NOT

- Not a certified cryptographic RNG
- Not security-audited for production
- Not a replacement for OS secure RNGs (`os.urandom`, `secrets`)

---

# 📎 Third-party notices

This repository includes third-party code:

- **stevenang/randomness_testsuite** (vendored into `randomrad/_vendor/randomness_testsuite`) for NIST-style statistical randomness tests.
  - The upstream license file is included in the vendored directory.

---

# Summary

`randomrad` is a modular entropy consumption framework.

It supports file-based development and ESP32-based hardware streaming, provides a random-like API without PRNG state, and validates statistical quality through automated tests and reports.

