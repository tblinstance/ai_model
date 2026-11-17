"""Pro tier model: vectorized NumPy + TensorFlow + PyTorch ensemble."""

from __future__ import annotations

from ..schemas import FrameworkBackend, ModelTier
from .base_model import BaseAIModel


class ProModel(BaseAIModel):
    """Mid-tier model blending NumPy vector compute with TensorFlow and PyTorch."""

    tier = ModelTier.PRO

    def _framework_order(self, override: FrameworkBackend | None) -> list[str]:
        if override and override != FrameworkBackend.HYBRID:
            return [override.value]
        return ["numpy", "tensorflow", "pytorch"]

