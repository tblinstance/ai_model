"""API request and response models mapping HTTP inputs to ai_engine tasks."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from ai_engine import ChatMessage, FrameworkBackend, GenerationResponse, ModelTier, TaskType


class BaseTaskRequest(BaseModel):
    """Common inference controls across Chat, Images, Video, and Code."""

    prompt: str = Field(..., min_length=1, max_length=16000)
    tier: ModelTier = ModelTier.FLASH
    backend: FrameworkBackend | None = None
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseTaskRequest):
    """Request payload for chat and SSE streaming completions."""

    conversation_id: str | int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    system_prompt: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=16, le=8192)


class ImageRequest(BaseTaskRequest):
    """Request payload for PNG image synthesis."""

    width: int | None = Field(default=None, ge=64, le=1024)
    height: int | None = Field(default=None, ge=64, le=1024)


class VideoRequest(BaseTaskRequest):
    """Request payload for long-form H.264 MP4 video synthesis (minimum 10 minutes)."""

    width: int | None = Field(default=None, ge=64, le=1280)
    height: int | None = Field(default=None, ge=64, le=720)
    frames: int | None = Field(default=None, ge=4, le=360)
    duration_seconds: int | None = Field(default=None, ge=1, le=3600)


class CodeRequest(BaseTaskRequest):
    """Request payload for multi-language code synthesis."""

    conversation_id: str | int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    language: str | None = None
    max_tokens: int = Field(default=1024, ge=32, le=8192)


class AgentRunRequest(BaseModel):
    """Request payload for autonomous agent task orchestration."""

    agent_name: str = Field(default="Generalist Agent", min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1, max_length=16000)
    tier: ModelTier = ModelTier.PRO
    task: TaskType | None = None
    conversation_id: str | int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    system_prompt: str | None = None
    backend: FrameworkBackend | None = None


class AgentRunResponse(BaseModel):
    """Result of an orchestrated agent step including chosen modality."""

    agent_name: str
    resolved_task: TaskType
    result: GenerationResponse


class HealthResponse(BaseModel):
    """Service health and active AI backend report."""

    status: str
    service: str
    version: str
    backends: dict[str, dict[str, Any]]
    media: dict[str, Any] = Field(default_factory=dict)
    frontier_libraries: dict[str, Any] = Field(default_factory=dict)

