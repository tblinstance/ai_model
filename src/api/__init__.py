"""FastAPI service layer exposing AI-Model inference endpoints."""

from .main import app, create_app

__all__ = ["app", "create_app"]

