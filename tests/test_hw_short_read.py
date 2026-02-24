import randomrad.backends.hw_backend as hw
import randomrad as rr


class FakeSerial:
    def __init__(self):
        self.buffer = b"D 10\n0123456789"
        self.ptr = 0
        self.is_open = True

    def write(self, data):
        pass

    def flush(self):
        pass

    def readline(self):
        return b"D 10\n"

    def read(self, n):
        # Liefert absichtlich nur kleine Stücke
        if self.ptr >= 10:
            return b""
        chunk = self.buffer[5 + self.ptr:5 + self.ptr + 3]  # max 3 bytes
        self.ptr += len(chunk)
        return chunk

    def reset_input_buffer(self):
        pass


def test_hw_short_reads(monkeypatch):
    monkeypatch.setenv("RANDOMRAD_BACKEND", "hw")
    monkeypatch.setenv("RANDOMRAD_PORT", "FAKE")

    fake = FakeSerial()

    monkeypatch.setattr(hw, "_SER", fake)

    def fake_ser():
        return fake

    monkeypatch.setattr(hw, "_ser", fake_ser)

    rr.clear_backend_override()

    data = rr.randbytes(10)

    assert data == b"0123456789"