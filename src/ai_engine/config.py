"""Central configuration and tier capability matrix for ai_engine."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import FrameworkBackend, ModelTier, TaskType, TierSpec


def _default_media_dir() -> Path:
    return Path(__file__).resolve().parent / "media"


def _default_checkpoint_dir() -> Path:
    return Path(__file__).resolve().parent / "checkpoints"


class EngineSettings(BaseSettings):
    """Runtime settings controlling device selection, media output, and backends."""

    model_config = SettingsConfigDict(env_prefix="AI_ENGINE_", extra="ignore")

    device_preference: str = os.getenv("AI_ENGINE_DEVICE", "auto")
    default_tier: ModelTier = ModelTier.FLASH
    keras_backend: str = os.getenv("KERAS_BACKEND", "torch")
    media_dir: Path = _default_media_dir()
    checkpoint_dir: Path = _default_checkpoint_dir()
    media_url_prefix: str = "/media/generated"
    vocab_size: int = 2048


TIER_SPECS: dict[ModelTier, TierSpec] = {
    ModelTier.FLASH: TierSpec(
        tier=ModelTier.FLASH,
        model_id="ai-model-flash-v1",
        display_name="tblinc Flash",
        description="tblinc AI — instant chat, rapid code drafts, and quick previews.",
        hidden_dim=64,
        num_layers=2,
        num_heads=4,
        vocab_size=2048,
        max_tokens=1024,
        image_resolution=(256, 256),
        video_frames=12,
        video_fps=8,
        credit_cost={
            TaskType.CHAT: 1,
            TaskType.CODE: 2,
            TaskType.IMAGES: 4,
            TaskType.VIDEO: 8,
            TaskType.AUDIO: 2,
        },
        primary_backend=FrameworkBackend.NUMPY,
        supported_tasks=[TaskType.CHAT, TaskType.IMAGES, TaskType.VIDEO, TaskType.CODE, TaskType.AUDIO],
    ),
    ModelTier.PRO: TierSpec(
        tier=ModelTier.PRO,
        model_id="ai-model-pro-v1",
        display_name="tblinc Pro",
        description="tblinc AI — deeper reasoning, production code, and high-detail media.",
        hidden_dim=128,
        num_layers=4,
        num_heads=8,
        vocab_size=2048,
        max_tokens=4096,
        image_resolution=(384, 384),
        video_frames=18,
        video_fps=12,
        credit_cost={
            TaskType.CHAT: 3,
            TaskType.CODE: 5,
            TaskType.IMAGES: 10,
            TaskType.VIDEO: 20,
            TaskType.AUDIO: 5,
        },
        primary_backend=FrameworkBackend.TENSORFLOW,
        supported_tasks=[TaskType.CHAT, TaskType.IMAGES, TaskType.VIDEO, TaskType.CODE, TaskType.AUDIO],
    ),
    ModelTier.ADVANCE: TierSpec(
        tier=ModelTier.ADVANCE,
        model_id="ai-model-advance-v1",
        display_name="tblinc Advance",
        description="tblinc AI — complex synthesis, multi-file architecture, and studio media.",
        hidden_dim=256,
        num_layers=6,
        num_heads=8,
        vocab_size=2048,
        max_tokens=8192,
        image_resolution=(512, 512),
        video_frames=24,
        video_fps=15,
        credit_cost={
            TaskType.CHAT: 6,
            TaskType.CODE: 10,
            TaskType.IMAGES: 18,
            TaskType.VIDEO: 36,
            TaskType.AUDIO: 10,
        },
        primary_backend=FrameworkBackend.HYBRID,
        supported_tasks=[TaskType.CHAT, TaskType.IMAGES, TaskType.VIDEO, TaskType.CODE, TaskType.AUDIO],
    ),
}

