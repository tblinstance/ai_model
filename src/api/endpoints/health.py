"""Health and neural backend inspection endpoints."""

from fastapi import APIRouter, Depends

from ai_engine import AIEngineRouter
from ..dependencies import get_engine_router
from ..schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(engine: AIEngineRouter = Depends(get_engine_router)) -> HealthResponse:
    """Return service status along with NumPy, PyTorch, TensorFlow, Keras, and frontier AI diagnostics."""
    return HealthResponse(
        status="ok",
        service="ai-model-fastapi",
        version="0.1.0",
        backends=engine.health(),
        media=engine.media_health(),
        frontier_libraries=engine.frontier_libraries_health(),
    )


@router.get("/frontier")
async def list_frontier(engine: AIEngineRouter = Depends(get_engine_router)) -> dict[str, dict[str, object]]:
    """Return all installed frontier AI libraries and their versions."""
    return engine.frontier_libraries_health()


@router.get("/backends")
async def list_backends(engine: AIEngineRouter = Depends(get_engine_router)) -> dict[str, dict[str, object]]:
    """Return detailed framework readiness and device placement."""
    return engine.health()

