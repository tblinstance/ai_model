"""Shared base model class coordinating PyTorch, TensorFlow, and Keras backends."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from ..backends import BaseNeuralBackend, BackendResult
from ..config import TIER_SPECS
from ..schemas import FrameworkBackend, ModelSummary, ModelTier, TierSpec
from ..utils import NeuralTokenizer, estimate_parameter_count


@dataclass(slots=True)
class EnsembleInference:
    """Combined neural representation produced across one or more frameworks."""

    frameworks_invoked: list[str]
    device: str
    parameter_count: int
    latent_vector: list[float]
    latent_norm: float
    confidence_score: float


class BaseAIModel:
    """Abstract base implementation shared across Flash, Pro, and Advance model tiers."""

    tier: ModelTier = ModelTier.FLASH

    def __init__(
        self,
        backends: dict[str, BaseNeuralBackend],
        tokenizer: NeuralTokenizer,
    ) -> None:
        self.backends = backends
        self.tokenizer = tokenizer
        self.spec: TierSpec = TIER_SPECS[self.tier]

    def summary(self) -> ModelSummary:
        """Return public metadata describing this model tier."""
        return ModelSummary(
            model_id=self.spec.model_id,
            tier=self.spec.tier,
            display_name=self.spec.display_name,
            description=self.spec.description,
            primary_backend=self.spec.primary_backend,
            supported_tasks=self.spec.supported_tasks,
            credit_cost=self.spec.credit_cost,
            hidden_dim=self.spec.hidden_dim,
            num_layers=self.spec.num_layers,
            max_tokens=self.spec.max_tokens,
            parameter_estimate=estimate_parameter_count(
                self.spec.hidden_dim,
                self.spec.num_layers,
                self.spec.vocab_size,
            ),
        )

    def _framework_order(self, override: FrameworkBackend | None) -> list[str]:
        if override and override != FrameworkBackend.HYBRID:
            return [override.value]
        return ["numpy"]

    def _resolve_backends(self, backend_override: FrameworkBackend | None) -> list[BaseNeuralBackend]:
        """Return available backends matching override, or fall back to an available backend."""
        selected: list[BaseNeuralBackend] = []
        for name in self._framework_order(backend_override):
            backend = self.backends.get(name)
            if backend is not None and backend.health().available:
                selected.append(backend)

        if not selected:
            for backend in self.backends.values():
                if backend.health().available:
                    selected.append(backend)
                    break

        if not selected:
            raise RuntimeError("No deep learning backend is currently available.")
        return selected

    def run_neural_encoding(
        self,
        prompt: str,
        backend_override: FrameworkBackend | None = None,
        seed: int | None = None,
    ) -> EnsembleInference:
        """Tokenize prompt and run one or more deep-learning backends."""
        token_ids = self.tokenizer.encode(prompt, max_length=64)
        results = [
            backend.encode_tokens(
                token_ids=token_ids,
                hidden_dim=self.spec.hidden_dim,
                num_layers=self.spec.num_layers,
                vocab_size=self.spec.vocab_size,
                seed=seed,
            )
            for backend in self._resolve_backends(backend_override)
        ]

        avg_latent = np.mean([r.latent_vector for r in results], axis=0)
        return EnsembleInference(
            frameworks_invoked=[r.backend for r in results],
            device=results[0].device,
            parameter_count=sum(r.parameter_count for r in results),
            latent_vector=[round(float(v), 5) for v in avg_latent.tolist()],
            latent_norm=round(float(np.mean([r.latent_norm for r in results])), 4),
            confidence_score=round(float(np.mean([r.confidence_score for r in results])), 4),
        )

    def synthesize_spatial(
        self,
        prompt: str,
        width: int,
        height: int,
        backend_override: FrameworkBackend | None = None,
        seed: int | None = None,
    ) -> tuple[np.ndarray, list[str]]:
        """Synthesize a blended [0, 1] RGB field using configured backend(s)."""
        token_ids = self.tokenizer.encode(prompt, max_length=64)
        fields: list[np.ndarray] = []
        used: list[str] = []
        for backend in self._resolve_backends(backend_override):
            fields.append(backend.synthesize_spatial_field(token_ids, width, height, 3, seed))
            used.append(backend.name)

        blended = np.mean(fields, axis=0)
        return np.clip(blended, 0.0, 1.0).astype(np.float32), used

