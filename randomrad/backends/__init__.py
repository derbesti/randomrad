"""
Backend provides raw entropy bytes.

Beide Backends nutzt get_bytes(n:int) -> bytes

Raise NotEnoughEntropy wenn nicht genug n byytes.
Blocking/retry passiert in entropy.py

"""