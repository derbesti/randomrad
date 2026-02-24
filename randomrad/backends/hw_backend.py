"""
Hardware backend (ESP32 MicroPython entropy streamer).

Protocol (ASCII header + raw bytes):
  Host -> "R <n>\\n"
  Device -> "D <n>\\n" + n bytes
  Device may also output "READY\\n" on boot.

Env vars:
- RANDOMRAD_PORT: e.g. COM4
- RANDOMRAD_BAUD: default 115200
- RANDOMRAD_SERIAL_TIMEOUT: default 1.0 seconds (per read call)
"""

from __future__ import annotations
from randomrad.exceptions import NotEnoughEntropy

import os
import time
import serial  # type: ignore


#stores a single serial connection across calls to avoid:
#opening a serial port is slow
#opening a serial port can reset ESP32 boards
#keeping it open preserves stream-like behavior
#you avoid constant reconnect + boot spam
_SER: serial.Serial | None = None


def _ser() -> serial.Serial:
    global _SER
    #if _SER exists and is open -> reuse it
    if _SER is not None and _SER.is_open:
        return _SER
    #otherwise read configuration from environment variables
    port = os.environ.get("RANDOMRAD_PORT")
    if not port:
        raise NotEnoughEntropy("RANDOMRAD_PORT not set (e.g. COM4)")

    baud = int(os.environ.get("RANDOMRAD_BAUD", "115200"))
    timeout = float(os.environ.get("RANDOMRAD_SERIAL_TIMEOUT", "1.0"))

    #open serial port
    _SER = serial.Serial(port, baudrate=baud, timeout=timeout)

    # Prevent auto-reset on some ESP32 boards when opening the port
    try:
        _SER.dtr = False
        _SER.rts = False
    except Exception:
        pass

    #booting time. dont read boot garbage
    time.sleep(0.8)

    #discard any boot messages/noise
    try:
        _SER.reset_input_buffer()
    except Exception:
        pass

    #return the serial instance
    return _SER


def get_bytes(n: int) -> bytes:
    """
    This function guarantees:
    exact byte count
    chunked request
    correct framing
    :param n:
    :return:
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if n == 0:
        return b""

    ser = _ser()

    # Chunking: large requests are split into smaller device-friendly blocks.
    # ESP32 side currently supports up to 4096 per request.
    max_chunk = int(os.environ.get("RANDOMRAD_HW_MAX_CHUNK", "2048"))
    if max_chunk <= 0:
        max_chunk = 2048
    if max_chunk > 4096:
        max_chunk = 4096

    out = bytearray()
    remaining = n

    while remaining > 0:
        chunk = remaining if remaining < max_chunk else max_chunk

        # Request bytes
        ser.write(f"R {chunk}\n".encode("ascii"))
        #ensure it actually leaves the buffer immediately
        ser.flush()

        # Read header line: may see boot logs/noise, so keep reading until "D <chunk>"
        deadline = time.monotonic() + 5.0
        header = b""
        #resync logic. ignore everythin until D
        while time.monotonic() < deadline:
            header = ser.readline()
            if not header:
                continue
            h = header.strip()
            if h.startswith(b"D "):
                break
            # ignore READY / boot logs / anything else
        else:
            raise NotEnoughEntropy("No valid data header from device (timeout)")

        #Found header line, now parse it
        parts = header.strip().split()
        if len(parts) != 2 or parts[0] != b"D":
            raise NotEnoughEntropy(f"Unexpected header from device: {header!r}")

        try:
            expected = int(parts[1])
        except Exception:
            raise NotEnoughEntropy(f"Invalid header length: {header!r}")

        if expected != chunk:
            raise NotEnoughEntropy(f"Device replied with different length: {expected} != {chunk}")

        # Read exactly chunk bytes (handle short reads)
        data = bytearray()
        deadline = time.monotonic() + 5.0  # total payload timeout

        while len(data) < chunk:
            if time.monotonic() >= deadline:
                break

            part = ser.read(chunk - len(data))
            if part:
                data.extend(part)

        data = bytes(data)

        if len(data) != chunk:
            raise NotEnoughEntropy(f"Device provided only {len(data)} of {chunk} bytes (timeout)")

        #final assembly
        #each chunks data append to put and decrement remaining
        out.extend(data)
        remaining -= chunk

    return bytes(out)
