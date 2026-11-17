"""Root API v1 router aggregating all FastAPI endpoint modules."""

from fastapi import APIRouter

from . import agent, audio, chat, code, health, images, models, rag, training, video

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(models.router)
api_router.include_router(chat.router)
api_router.include_router(images.router)
api_router.include_router(video.router)
api_router.include_router(audio.router)
api_router.include_router(rag.router)
api_router.include_router(code.router)
api_router.include_router(agent.router)
api_router.include_router(training.router)

