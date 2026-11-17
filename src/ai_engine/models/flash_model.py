"""Flash tier model: ultra-low-latency vectorized NumPy fast inference."""

from __future__ import annotations

from ..schemas import FrameworkBackend, ModelTier
from .base_model import BaseAIModel


class FlashModel(BaseAIModel):
    """Lightweight fast-path model optimized for instant NumPy CPU response times."""

    tier = ModelTier.FLASH

    def _framework_order(self, override: FrameworkBackend | None) -> list[str]:
        if override and override != FrameworkBackend.HYBRID:
            return [override.value]
        return ["numpy"]

