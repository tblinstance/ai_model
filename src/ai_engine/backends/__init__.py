"""Multi-framework neural backends (NumPy, PyTorch, TensorFlow, Keras) for ai_engine."""

from .backend_base import (
    BackendHealth,
    BackendResult,
    BackendTrainingOutcome,
    BaseNeuralBackend,
    adaptive_batch_size,
    prepare_training_batch,
)
from .backend_keras import KerasBackend
from .backend_numpy import NumPyBackend
from .backend_pytorch import PyTorchBackend
from .backend_tensorflow import TensorFlowBackend

__all__ = [
    "BackendHealth",
    "BackendResult",
    "BackendTrainingOutcome",
    "BaseNeuralBackend",
    "KerasBackend",
    "NumPyBackend",
    "PyTorchBackend",
    "TensorFlowBackend",
    "adaptive_batch_size",
    "prepare_training_batch",
]

