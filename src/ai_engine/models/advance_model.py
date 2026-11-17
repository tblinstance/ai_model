"""Advance tier model: full NumPy + PyTorch + TensorFlow + Keras ensemble."""

from __future__ import annotations

from ..schemas import FrameworkBackend, ModelTier
from .base_model import BaseAIModel


class AdvanceModel(BaseAIModel):
    """Flagship ensemble model fusing NumPy, PyTorch, TensorFlow, and Keras outputs."""

    tier = ModelTier.ADVANCE

    def _framework_order(self, override: FrameworkBackend | None) -> list[str]:
        if override and override != FrameworkBackend.HYBRID:
            return [override.value]
        return ["numpy", "pytorch", "tensorflow", "keras"]

