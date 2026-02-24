# main.py (ESP32 MicroPython) — entropy stream server
#
# Protocol:
#   Host -> "R <n>\n"
#   Device -> "D <n>\n" + n raw bytes

import sys
import os
import time
import uhashlib

#harvest entropy from timing jitter
def jitter_bytes(n=64):
    out = bytearray()
    last = time.ticks_us()
    # repeatedly calls time.tick_us()
    for _ in range(n):
        now = time.ticks_us()
        #computes the time difference from the previos measurement
        d = time.ticks_diff(now, last)
        last = now
        #takes only the low 8 bits and appends them
        out.append(d & 0xFF)
        for _ in range(50):
            pass
    return bytes(out)

#hardware RNG
def urandom_bytes(n=64):
    try:
        return os.urandom(n)
    except Exception:
        return b""

#whitening + expansion step using SHA-256
#SHA-256 is good at destroying structure/bias
def whiten_to_bytes(raw, out_len):
    out = bytearray()
    counter = 0
    #small amount of entropy input becomes a larger output stream
    while len(out) < out_len:
        h = uhashlib.sha256()
        h.update(raw)
        h.update(counter.to_bytes(4, "big"))
        out.extend(h.digest())
        counter += 1
    return bytes(out[:out_len])

#assembles raw input
def get_entropy(n):
    raw = bytearray()
    raw.extend(urandom_bytes(64))
    raw.extend(jitter_bytes(64))
    if len(raw) == 0:
        raw.extend(jitter_bytes(128))
        #call whiten to produce exactly n bytes
    return whiten_to_bytes(bytes(raw), n)

#reads sys.stdin one character at a time until \n
def read_line():
    buf = bytearray()
    while True:
        ch = sys.stdin.read(1)
        if not ch:
            continue
        if ch == "\n":
            return buf.decode().strip()
        if ch != "\r":
            if isinstance(ch, str):
                buf.extend(ch.encode())
            else:
                buf.extend(ch)


def send_line(s):
    # No flush: some MicroPython builds don't expose flush on sys.stdout
    sys.stdout.write(s + "\n")


def main():
    send_line("READY")

    #infinite loop, only sends valid D <n>
    while True:
        line = read_line()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 2 or parts[0] != "R":
            send_line("ERR")
            continue

        try:
            n = int(parts[1])
        except Exception:
            send_line("ERR")
            continue

        if n <= 0 or n > 4096:
            send_line("ERR")
            continue

        data = get_entropy(n)

        # Header (text)
        send_line("D %d" % n)

        # Raw bytes (binary)
        sys.stdout.buffer.write(data)
        # (No flush here either)


main()