"""Abstract base classes and shared structures for deep-learning backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np


@dataclass(slots=True)
class BackendHealth:
    """Availability and hardware diagnostic info for a neural backend."""

    name: str
    available: bool
    version: str
    device: str
    details: dict[str, str | bool | int] = field(default_factory=dict)


@dataclass(slots=True)
class BackendResult:
    """Structured output returned by any neural backend forward pass."""

    backend: str
    device: str
    parameter_count: int
    latent_vector: list[float]
    latent_norm: float
    confidence_score: float
    spatial_map: np.ndarray | None = None


@dataclass(slots=True)
class BackendTrainingOutcome:
    """Metrics returned by a gradient-based backend training run."""

    backend: str
    device: str
    epochs: int
    initial_loss: float
    final_loss: float
    accuracy: float
    samples_seen: int
    parameter_count: int
    checkpoint_path: str | None = None


def prepare_training_batch(
    examples: list[tuple[list[int], int]],
    seq_len: int = 32,
    vocab_size: int = 2048,
) -> tuple[np.ndarray, np.ndarray]:
    """Pad or truncate token sequences into uniform NumPy (N, seq_len) and (N,) label arrays."""
    if not examples:
        raise ValueError("Training requires at least one labeled example.")

    x_arr = np.zeros((len(examples), seq_len), dtype=np.int64)
    y_arr = np.zeros((len(examples),), dtype=np.int64)
    for row_idx, (token_ids, label) in enumerate(examples):
        clipped = [max(1, min(vocab_size - 1, tid)) for tid in token_ids[:seq_len]] or [1]
        x_arr[row_idx, : len(clipped)] = clipped
        y_arr[row_idx] = max(0, min(15, int(label)))
    return x_arr, y_arr


def effective_learning_rate(
    base_lr: float,
    hidden_dim: int,
    num_layers: int,
    backend_scale: float = 1.0,
) -> float:
    """Scale optimizer learning rate inversely with model depth and width to keep deep tiers stable."""
    depth_width_factor = ((64.0 / max(32.0, float(hidden_dim))) ** 0.5) * (
        (2.0 / max(1.0, float(num_layers))) ** 0.5
    )
    scaled = base_lr * depth_width_factor * backend_scale
    return max(0.0004, min(0.05, round(scaled, 6)))


def adaptive_batch_size(num_samples: int, max_batch: int = 512) -> int:
    """Scale mini-batch size cleanly so large JSON corpora train rapidly without underfitting."""
    if num_samples <= 32:
        return max(1, num_samples)
    if num_samples < 128:
        return 16
    return min(max_batch, max(32, num_samples // 10))


class BaseNeuralBackend(ABC):
    """Unified contract implemented by PyTorch, TensorFlow, and Keras backends."""

    name: str = "base"

    @abstractmethod
    def health(self) -> BackendHealth:
        """Report framework version, device placement, and readiness."""

    @abstractmethod
    def encode_tokens(
        self,
        token_ids: list[int],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        seed: int | None = None,
    ) -> BackendResult:
        """Run a neural forward pass over token IDs and return latent representations."""

    @abstractmethod
    def synthesize_spatial_field(
        self,
        token_ids: list[int],
        width: int,
        height: int,
        channels: int = 3,
        seed: int | None = None,
    ) -> np.ndarray:
        """Generate a normalized [0, 1] spatial tensor of shape (height, width, channels)."""

    @abstractmethod
    def train_on_examples(
        self,
        examples: list[tuple[list[int], int]],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        epochs: int = 6,
        learning_rate: float = 0.01,
        checkpoint_path: Path | None = None,
    ) -> BackendTrainingOutcome:
        """Train backend weights with backpropagation on (token_ids, intent_id) pairs."""

    def load_weights(
        self,
        checkpoint_path: Path,
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
    ) -> bool:
        """Load persisted weights into memory when a checkpoint exists."""
        return False

    def clear_cache(self) -> None:
        """Reset in-memory cached weights/models so fresh training initializes cleanly."""
        return None

