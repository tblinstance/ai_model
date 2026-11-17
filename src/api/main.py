"""FastAPI application factory and lifespan manager for AI-Model inference."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ai_engine import AIEngineRouter, EngineSettings
from .clients import DjangoClient
from .config import APISettings
from .endpoints import api_router


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    cfg = settings or APISettings()
    cfg.media_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        kwargs = {"media_dir": cfg.media_dir}
        if cfg.checkpoint_dir is not None:
            kwargs["checkpoint_dir"] = cfg.checkpoint_dir
        engine_settings = EngineSettings(**kwargs)
        app.state.engine_router = AIEngineRouter(settings=engine_settings)
        app.state.django_client = DjangoClient(
            base_url=cfg.django_base_url,
            internal_api_key=cfg.internal_api_key,
            timeout=cfg.request_timeout_seconds,
        )
        yield
        await app.state.django_client.close()

    app = FastAPI(
        title=cfg.app_title,
        version=cfg.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.mount("/media/generated", StaticFiles(directory=str(cfg.media_dir)), name="media")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "ai-model-fastapi",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()

