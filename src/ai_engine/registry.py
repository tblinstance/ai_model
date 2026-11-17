"""Central registry managing neural backends, tiered models, and task pipelines."""

from __future__ import annotations

from pathlib import Path

from .backends import (
    BackendHealth,
    BaseNeuralBackend,
    KerasBackend,
    NumPyBackend,
    PyTorchBackend,
    TensorFlowBackend,
)
from .config import EngineSettings
from .exceptions import ModelNotFoundError
from .models import AdvanceModel, BaseAIModel, FlashModel, ProModel
from .pipelines import (
    AudioPipeline,
    BasePipeline,
    ChatPipeline,
    CodePipeline,
    ImagesPipeline,
    VideoPipeline,
)
from .schemas import ModelSummary, ModelTier, TaskType
from .training import NeuralTrainer
from .utils import ArtifactStorage, NeuralTokenizer, VectorMemory


class ModelRegistry:
    """Holds singleton backends, Flash/Pro/Advance models, trainer, and multimodal pipelines."""

    def __init__(self, settings: EngineSettings | None = None) -> None:
        self.settings = settings or EngineSettings()
        self.tokenizer = NeuralTokenizer(vocab_size=self.settings.vocab_size)
        self.storage = ArtifactStorage(
            root_dir=self.settings.media_dir,
            url_prefix=self.settings.media_url_prefix,
        )

        self.backends: dict[str, BaseNeuralBackend] = {
            "numpy": NumPyBackend(device_preference=self.settings.device_preference),
            "pytorch": PyTorchBackend(device_preference=self.settings.device_preference),
            "tensorflow": TensorFlowBackend(device_preference=self.settings.device_preference),
            "keras": KerasBackend(device_preference=self.settings.device_preference),
        }

        self.models: dict[ModelTier, BaseAIModel] = {
            ModelTier.FLASH: FlashModel(self.backends, self.tokenizer),
            ModelTier.PRO: ProModel(self.backends, self.tokenizer),
            ModelTier.ADVANCE: AdvanceModel(self.backends, self.tokenizer),
        }

        self.trainer = NeuralTrainer(
            checkpoint_dir=self.settings.checkpoint_dir,
            tokenizer=self.tokenizer,
        )
        self.trainer.load_saved_state(self.backends, self.models)

        self.vector_memory = VectorMemory()
        kb_path = Path(self.settings.checkpoint_dir) / "knowledge_base.json"
        if kb_path.exists():
            self.vector_memory.load_knowledge_base(kb_path, max_items=120)

        images_pipeline = ImagesPipeline(self.storage, self.tokenizer, trainer=self.trainer)
        video_pipeline = VideoPipeline(self.storage, self.tokenizer, trainer=self.trainer)
        self.pipelines: dict[TaskType, BasePipeline] = {
            TaskType.CHAT: ChatPipeline(
                self.storage,
                self.tokenizer,
                trainer=self.trainer,
                images_pipeline=images_pipeline,
                video_pipeline=video_pipeline,
            ),
            TaskType.IMAGES: images_pipeline,
            TaskType.VIDEO: video_pipeline,
            TaskType.CODE: CodePipeline(self.storage, self.tokenizer, trainer=self.trainer),
            TaskType.AUDIO: AudioPipeline(self.storage, self.tokenizer, trainer=self.trainer),
        }

    def get_model(self, tier: ModelTier) -> BaseAIModel:
        """Look up a registered model tier or raise ModelNotFoundError."""
        model = self.models.get(tier)
        if model is None:
            raise ModelNotFoundError(f"Unknown model tier: {tier}")
        return model

    def get_pipeline(self, task: TaskType) -> BasePipeline:
        """Look up a task pipeline or raise ModelNotFoundError."""
        pipeline = self.pipelines.get(task)
        if pipeline is None:
            raise ModelNotFoundError(f"Unsupported task type: {task}")
        return pipeline

    def list_models(self) -> list[ModelSummary]:
        """Return summaries for Flash, Pro, and Advance tiers."""
        return [self.models[tier].summary() for tier in (ModelTier.FLASH, ModelTier.PRO, ModelTier.ADVANCE)]

    def backend_health(self) -> dict[str, BackendHealth]:
        """Inspect health and versions across PyTorch, TensorFlow, and Keras."""
        return {name: backend.health() for name, backend in self.backends.items()}

