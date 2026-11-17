"""Top-level inference router orchestrating models and multimodal pipelines."""

from __future__ import annotations

from collections.abc import Iterator

from .config import EngineSettings
from .exceptions import GenerationError, UnsupportedBackendError
from .pipelines import ChatPipeline
from .pipelines.media_renderer import pillow_capabilities
from .registry import ModelRegistry
from .schemas import (
    AllTiersTrainingResult,
    CheckpointInfo,
    EvaluationRequest,
    EvaluationResult,
    FrameworkBackend,
    GenerationRequest,
    GenerationResponse,
    ModelSummary,
    ModelTier,
    TaskType,
    TrainingRequest,
    TrainingResult,
    TrainingStatusResponse,
)


class AIEngineRouter:
    """Facade exposed to FastAPI, Django, and Agent services for model execution."""

    def __init__(self, settings: EngineSettings | None = None) -> None:
        self.registry = ModelRegistry(settings=settings)

    def _resolve_backend_fallback(self, backend: FrameworkBackend | None) -> str | None:
        """Validate requested backend or return its name when gracefully falling back."""
        has_any_available = any(b.health().available for b in self.registry.backends.values())
        if not has_any_available:
            raise UnsupportedBackendError("No deep learning backend is currently available.")

        if backend is None or backend == FrameworkBackend.HYBRID:
            return None

        target = self.registry.backends.get(backend.value)
        if target is None or not target.health().available:
            return backend.value
        return None

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Dispatch a generation request to the selected tier and task pipeline."""
        fallback_from = self._resolve_backend_fallback(request.backend)
        model = self.registry.get_model(request.tier)
        pipeline = self.registry.get_pipeline(request.task)
        try:
            response = pipeline.run(model=model, request=request)
        except Exception as exc:
            raise GenerationError(f"Generation failed for {request.tier.value}/{request.task.value}: {exc}") from exc

        if fallback_from is not None:
            response.extra["fallback_from"] = fallback_from
            response.extra["fallback_reason"] = (
                f"Requested backend '{fallback_from}' is unavailable; fell back to "
                f"{response.diagnostics.backend_used}."
            )
        return response

    def stream_chat(self, request: GenerationRequest) -> Iterator[str]:
        """Stream chat output chunks for real-time Server-Sent Events responses."""
        self._resolve_backend_fallback(request.backend)
        model = self.registry.get_model(request.tier)
        pipeline = self.registry.get_pipeline(TaskType.CHAT)
        if not isinstance(pipeline, ChatPipeline):  # pragma: no cover
            raise GenerationError("Chat pipeline unavailable.")
        return pipeline.stream_tokens(model=model, request=request)

    def list_models(self) -> list[ModelSummary]:
        """Return metadata for all available model tiers."""
        return self.registry.list_models()

    def get_model_summary(self, tier: ModelTier) -> ModelSummary:
        """Return metadata for a specific model tier."""
        return self.registry.get_model(tier).summary()

    def health(self) -> dict[str, dict[str, object]]:
        """Return live framework diagnostics across NumPy, PyTorch, TensorFlow, and Keras."""
        report: dict[str, dict[str, object]] = {}
        for name, info in self.registry.backend_health().items():
            report[name] = {
                "available": info.available,
                "version": info.version,
                "device": info.device,
                "details": info.details,
            }
        return report

    def media_health(self) -> dict[str, object]:
        """Return Pillow image/video media renderer capabilities."""
        return pillow_capabilities()

    def train(self, request: TrainingRequest) -> TrainingResult:
        """Train available neural backends on built-in and custom labeled examples."""
        try:
            return self.registry.trainer.train(
                request=request,
                backends=self.registry.backends,
                models=self.registry.models,
            )
        except Exception as exc:
            raise GenerationError(f"Training failed for {request.tier.value}: {exc}") from exc

    def training_status(self) -> TrainingStatusResponse:
        """Return persisted training telemetry, learned intents, and checkpoint path."""
        return self.registry.trainer.status()

    def train_all(self, request: TrainingRequest) -> AllTiersTrainingResult:
        """Train Flash, Pro, and Advance tiers across available neural backends."""
        try:
            return self.registry.trainer.train_all(
                request=request,
                backends=self.registry.backends,
                models=self.registry.models,
            )
        except Exception as exc:
            raise GenerationError(f"Multi-tier training failed: {exc}") from exc

    def evaluate_training(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate intent classification and sample matching for a prompt."""
        return self.registry.trainer.evaluate(request=request, models=self.registry.models)

    def list_checkpoints(self) -> list[CheckpointInfo]:
        """List saved weight and metadata checkpoints on disk."""
        return self.registry.trainer.list_checkpoints()

    def reset_training(self) -> dict[str, object]:
        """Clear saved checkpoints and reset backend weight caches."""
        return self.registry.trainer.reset(backends=self.registry.backends)

    def query_rag(self, query: str, top_k: int = 3, min_score: float = 0.1) -> list[dict[str, Any]]:
        """Query semantic vector memory store for relevant context."""
        return self.registry.vector_memory.search(query=query, top_k=top_k, min_score=min_score)

    def add_rag_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Add and embed a document into semantic vector memory."""
        self.registry.vector_memory.add_document(doc_id=doc_id, text=text, metadata=metadata)

    def scrape_rag_url(self, url: str, html_content: str | None = None) -> dict[str, Any]:
        """Scrape webpage content using BeautifulSoup4 and index it into vector memory."""
        return self.registry.vector_memory.scrape_and_index_url(url=url, html_content=html_content)

    def transcribe_audio(self, audio_data: bytes | str | Path, language: str | None = None) -> dict[str, Any]:
        """Transcribe speech audio using OpenAI Whisper."""
        pipeline = self.registry.get_pipeline(TaskType.AUDIO)
        if hasattr(pipeline, "transcribe"):
            return pipeline.transcribe(audio_data, language=language)
        return {"error": "Audio pipeline does not support transcription", "success": False}

    def analyze_audio(self, audio_data: bytes | str | Path) -> dict[str, Any]:
        """Perform acoustic analysis using Librosa and SoundFile."""
        pipeline = self.registry.get_pipeline(TaskType.AUDIO)
        if hasattr(pipeline, "analyze_audio"):
            return pipeline.analyze_audio(audio_data)
        return {"error": "Audio pipeline does not support acoustic analysis", "success": False}

    def frontier_libraries_health(self) -> dict[str, dict[str, Any]]:
        """Return availability and versions of all frontier AI packages."""
        pkgs = [
            ("transformers", "transformers"),
            ("diffusers", "diffusers"),
            ("accelerate", "accelerate"),
            ("whisper", "whisper"),
            ("edge_tts", "edge_tts"),
            ("librosa", "librosa"),
            ("soundfile", "soundfile"),
            ("insightface", "insightface"),
            ("onnxruntime", "onnxruntime"),
            ("torchvision", "torchvision"),
            ("torchaudio", "torchaudio"),
            ("safetensors", "safetensors"),
            ("vllm", "vllm"),
            ("bitsandbytes", "bitsandbytes"),
            ("sentence_transformers", "sentence_transformers"),
            ("chromadb", "chromadb"),
            ("peft", "peft"),
            ("datasets", "datasets"),
            ("google_genai", "google.genai"),
            ("beautifulsoup4", "bs4"),
        ]
        status: dict[str, dict[str, Any]] = {}
        for display_name, mod_name in pkgs:
            try:
                mod = __import__(mod_name)
                version = getattr(mod, "__version__", "installed")
                status[display_name] = {"available": True, "version": str(version)}
            except Exception as e:
                status[display_name] = {"available": False, "version": None, "error": str(e)}
        return status


