"""Custom exceptions raised by the AI engine subsystem."""


class AIEngineError(Exception):
    """Base exception for all AI engine errors."""


class ModelNotFoundError(AIEngineError):
    """Raised when an unknown model tier or task combination is requested."""


class UnsupportedBackendError(AIEngineError):
    """Raised when a requested deep-learning backend is unavailable."""


class GenerationError(AIEngineError):
    """Raised when model inference or media synthesis fails."""

