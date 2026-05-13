class InferenceError(Exception):
    """Raised when an inference call fails after retries."""


class UnsupportedOperation(InferenceError):
    """Raised when a client doesn't support the requested modality."""
