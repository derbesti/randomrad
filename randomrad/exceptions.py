class RandomradError(RuntimeError):
    pass

class NotEnoughEntropy(RandomradError):
    """Raised when backend cannot provide enough bytes now / at all."""
    pass

class BackendError(RandomradError):
    pass