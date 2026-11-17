"""Configuration settings for the FastAPI inference service."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_media_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "ai_engine" / "media"


class APISettings(BaseSettings):
    """Environment-driven settings for FastAPI, CORS, and Django bridge."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / "backend" / ".env"),
        env_prefix="FASTAPI_",
        extra="ignore",
    )

    app_title: str = "AI-Model FastAPI Inference Engine"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8001
    django_base_url: str = os.getenv("DJANGO_BASE_URL", "http://127.0.0.1:8000")
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "ai-model-internal-dev-key")
    cors_origins: list[str] = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    media_dir: Path = _default_media_dir()
    checkpoint_dir: Path | None = None
    request_timeout_seconds: float = 15.0

