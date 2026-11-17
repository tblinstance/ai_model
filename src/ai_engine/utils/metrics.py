"""Latency measurement, parameter estimation, and credit cost utilities."""

from __future__ import annotations

import time
from types import TracebackType

from ..config import TIER_SPECS
from ..schemas import ModelTier, TaskType


class LatencyTimer:
    """Context manager measuring wall-clock execution time in milliseconds."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> LatencyTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000.0, 3)


def estimate_parameter_count(hidden_dim: int, num_layers: int, vocab_size: int) -> int:
    """Approximate trainable neural parameter count for a tier specification."""
    embedding_params = vocab_size * hidden_dim
    layer_params = num_layers * (4 * hidden_dim * hidden_dim + 4 * hidden_dim)
    head_params = hidden_dim * 64 + 64
    return embedding_params + layer_params + head_params


def compute_credit_cost(tier: ModelTier, task: TaskType, multiplier: float = 1.0) -> int:
    """Compute final integer credit charge for a tier/task generation."""
    base = TIER_SPECS[tier].credit_cost[task]
    return max(1, round(base * multiplier))

