"""Model catalog endpoints exposing Flash, Pro, and Advance capabilities."""

from fastapi import APIRouter, Depends

from ai_engine import AIEngineRouter, ModelSummary, ModelTier
from ..dependencies import get_engine_router

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=list[ModelSummary])
async def list_models(engine: AIEngineRouter = Depends(get_engine_router)) -> list[ModelSummary]:
    """List Flash, Pro, and Advance model specifications and credit costs."""
    return engine.list_models()


@router.get("/{tier}", response_model=ModelSummary)
async def get_model(
    tier: ModelTier,
    engine: AIEngineRouter = Depends(get_engine_router),
) -> ModelSummary:
    """Inspect a specific model tier."""
    return engine.get_model_summary(tier)

