"""Shared base pipeline helpers for response assembly and telemetry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import uuid4

from ..models import BaseAIModel, EnsembleInference
from ..schemas import (
    GenerationRequest,
    GenerationResponse,
    NeuralDiagnostics,
    TaskType,
)
from ..utils import ArtifactStorage, LatencyTimer, NeuralTokenizer, compute_credit_cost

if TYPE_CHECKING:
    from ..training import NeuralTrainer


class BasePipeline(ABC):
    """Abstract base pipeline unifying telemetry, token accounting, and cost computation."""

    task: TaskType

    def __init__(
        self,
        storage: ArtifactStorage,
        tokenizer: NeuralTokenizer,
        trainer: NeuralTrainer | None = None,
    ) -> None:
        self.storage = storage
        self.tokenizer = tokenizer
        self.trainer = trainer

    @staticmethod
    def _compose_encoding_prompt(request: GenerationRequest) -> str:
        if not request.messages:
            return request.prompt
        recent = request.messages[-4:]
        history_text = "\n".join(f"{msg.role}: {msg.content}" for msg in recent)
        return f"{history_text}\nuser: {request.prompt}"

    def _count_input_tokens(self, request: GenerationRequest) -> int:
        total = self.tokenizer.count_tokens(request.prompt)
        if request.system_prompt:
            total += self.tokenizer.count_tokens(request.system_prompt)
        for msg in request.messages:
            total += self.tokenizer.count_tokens(msg.content)
        return total

    def run(self, model: BaseAIModel, request: GenerationRequest) -> GenerationResponse:
        """Execute neural encoding, run task synthesis, and wrap response telemetry."""
        encoding_input = self._compose_encoding_prompt(request)
        with LatencyTimer() as timer:
            encoding = model.run_neural_encoding(
                prompt=encoding_input,
                backend_override=request.backend,
                seed=request.seed,
            )
            payload = self._execute(model=model, request=request, encoding=encoding)

        tokens_in = self._count_input_tokens(request)
        out_text = payload.get("text") or payload.get("code") or ""
        tokens_out = self.tokenizer.count_tokens(str(out_text)) if out_text else 32
        backend_label = "+".join(encoding.frameworks_invoked)

        return GenerationResponse(
            request_id=uuid4().hex,
            model_id=model.spec.model_id,
            tier=model.spec.tier,
            task=self.task,
            text=payload.get("text"),
            code=payload.get("code"),
            language=payload.get("language"),
            artifact_url=payload.get("artifact_url"),
            artifact_path=payload.get("artifact_path"),
            preview_base64=payload.get("preview_base64"),
            mime_type=payload.get("mime_type"),
            credits_used=compute_credit_cost(model.spec.tier, self.task),
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            diagnostics=NeuralDiagnostics(
                backend_used=backend_label,
                frameworks_invoked=encoding.frameworks_invoked,
                device=encoding.device,
                parameter_count=encoding.parameter_count,
                latent_norm=encoding.latent_norm,
                confidence_score=encoding.confidence_score,
                latency_ms=timer.elapsed_ms,
            ),
            extra=payload.get("extra", {}),
        )

    @abstractmethod
    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object]:
        """Run modality-specific generation using the model and neural encoding."""

