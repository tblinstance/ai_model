"""Typed schemas for AI engine requests, responses, and model metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    """Supported model capacity and latency tiers."""

    FLASH = "flash"
    PRO = "pro"
    ADVANCE = "advance"


class TaskType(str, Enum):
    """Supported multimodal AI generation capabilities."""

    CHAT = "chat"
    IMAGES = "images"
    VIDEO = "video"
    CODE = "code"
    AUDIO = "audio"


class FrameworkBackend(str, Enum):
    """Supported neural computation backends."""

    NUMPY = "numpy"
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    KERAS = "keras"
    HYBRID = "hybrid"


class TierSpec(BaseModel):
    """Architectural specification for a model tier."""

    tier: ModelTier
    model_id: str
    display_name: str
    description: str
    hidden_dim: int
    num_layers: int
    num_heads: int
    vocab_size: int
    max_tokens: int
    image_resolution: tuple[int, int]
    video_frames: int
    video_fps: int
    credit_cost: dict[TaskType, int]
    primary_backend: FrameworkBackend
    supported_tasks: list[TaskType]


class ChatMessage(BaseModel):
    """Single message turn within a multi-turn conversation thread."""

    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(..., min_length=1, max_length=16000)


class GenerationRequest(BaseModel):
    """Unified input payload for any AI engine generation task."""

    prompt: str = Field(..., min_length=1, max_length=16000)
    tier: ModelTier = ModelTier.FLASH
    task: TaskType = TaskType.CHAT
    backend: FrameworkBackend | None = None
    conversation_id: str | int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    system_prompt: str | None = None
    language: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=16, le=8192)
    width: int | None = Field(default=None, ge=64, le=1280)
    height: int | None = Field(default=None, ge=64, le=1024)
    frames: int | None = Field(default=None, ge=4, le=360)
    duration_seconds: int | None = Field(default=None, ge=1, le=3600)
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NeuralDiagnostics(BaseModel):
    """Runtime neural tensor and framework telemetry for an inference call."""

    backend_used: str
    frameworks_invoked: list[str]
    device: str
    parameter_count: int
    latent_norm: float
    confidence_score: float
    latency_ms: float


class GenerationResponse(BaseModel):
    """Unified output payload produced by any AI engine pipeline."""

    request_id: str
    model_id: str
    tier: ModelTier
    task: TaskType
    text: str | None = None
    code: str | None = None
    language: str | None = None
    artifact_url: str | None = None
    artifact_path: str | None = None
    preview_base64: str | None = None
    mime_type: str | None = None
    credits_used: int
    tokens_input: int
    tokens_output: int
    diagnostics: NeuralDiagnostics
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelSummary(BaseModel):
    """Public metadata summarizing an available model tier."""

    model_id: str
    tier: ModelTier
    display_name: str
    description: str
    primary_backend: FrameworkBackend
    supported_tasks: list[TaskType]
    credit_cost: dict[TaskType, int]
    hidden_dim: int
    num_layers: int
    max_tokens: int
    parameter_estimate: int


class TrainingSample(BaseModel):
    """Labeled instruction/response pair used to fine-tune neural backends and memory."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    response: str = Field(..., min_length=1, max_length=16000)
    intent: str = Field(default="general", min_length=1, max_length=64)
    task: TaskType = TaskType.CHAT


class TrainingRequest(BaseModel):
    """Configuration payload for training PyTorch, TensorFlow, and Keras backends."""

    tier: ModelTier = ModelTier.FLASH
    backend: FrameworkBackend | None = None
    epochs: int = Field(default=14, ge=1, le=100)
    learning_rate: float = Field(default=0.012, gt=0.0, le=0.5)
    include_builtin_dataset: bool = True
    samples: list[TrainingSample] = Field(default_factory=list)
    save_checkpoint: bool = True


class BackendTrainingStats(BaseModel):
    """Training telemetry returned for a single deep-learning framework."""

    backend: str
    device: str
    epochs: int
    initial_loss: float
    final_loss: float
    accuracy: float
    samples_seen: int
    parameter_count: int
    checkpoint_path: str | None = None


class TrainingResult(BaseModel):
    """Aggregated outcome of a multi-backend training session."""

    training_id: str
    tier: ModelTier
    model_id: str
    dataset_size: int
    learned_intents: list[str]
    backends_trained: list[BackendTrainingStats]
    checkpoint_path: str | None = None
    duration_ms: float
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrainingStatusResponse(BaseModel):
    """Snapshot describing current trained weights and dataset state."""

    trained: bool
    dataset_size: int
    learned_intents: list[str]
    checkpoint_dir: str
    last_training: TrainingResult | None = None


class AllTiersTrainingResult(BaseModel):
    """Combined outcome when training Flash, Pro, and Advance tiers together."""

    training_id: str
    dataset_size: int
    learned_intents: list[str]
    tier_results: list[TrainingResult]
    total_duration_ms: float
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CheckpointInfo(BaseModel):
    """Metadata describing a saved model weight or knowledge file on disk."""

    filename: str
    backend: str
    tier: str
    size_bytes: int
    path: str
    modified_at: datetime


class EvaluationRequest(BaseModel):
    """Input payload for testing trained intent prediction and knowledge retrieval."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    tier: ModelTier = ModelTier.FLASH
    backend: FrameworkBackend | None = None
    expected_intent: str | None = None
    task: TaskType = TaskType.CHAT


class EvaluationResult(BaseModel):
    """Evaluation metrics comparing predicted neural intent and retrieved memory."""

    prompt: str
    tier: ModelTier
    predicted_intent: str
    intent_confidence: float
    expected_intent: str | None = None
    intent_matched: bool | None = None
    matched_sample_prompt: str | None = None
    matched_sample_score: float = 0.0
    confidence_score: float
    frameworks_invoked: list[str]
    generated_preview: str

