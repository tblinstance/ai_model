"""Neural training, multi-tier orchestration, evaluation, and checkpoint endpoints."""

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from ai_engine import (
    AIEngineRouter,
    AllTiersTrainingResult,
    CheckpointInfo,
    EvaluationRequest,
    EvaluationResult,
    TrainingRequest,
    TrainingResult,
    TrainingStatusResponse,
)
from ..dependencies import get_engine_router

router = APIRouter(prefix="/train", tags=["Training"])


@router.post("", response_model=TrainingResult)
async def train_engine(
    payload: TrainingRequest,
    engine: AIEngineRouter = Depends(get_engine_router),
) -> TrainingResult:
    """Run supervised gradient training across NumPy, PyTorch, TensorFlow, and Keras backends."""
    return await run_in_threadpool(engine.train, payload)


@router.post("/all", response_model=AllTiersTrainingResult)
async def train_all_tiers(
    payload: TrainingRequest,
    engine: AIEngineRouter = Depends(get_engine_router),
) -> AllTiersTrainingResult:
    """Train Flash, Pro, and Advance model tiers across selected backends."""
    return await run_in_threadpool(engine.train_all, payload)


@router.get("/status", response_model=TrainingStatusResponse)
async def training_status(
    engine: AIEngineRouter = Depends(get_engine_router),
) -> TrainingStatusResponse:
    """Inspect current training dataset metrics, learned intents, and checkpoints."""
    return await run_in_threadpool(engine.training_status)


@router.get("/checkpoints", response_model=list[CheckpointInfo])
async def list_checkpoints(
    engine: AIEngineRouter = Depends(get_engine_router),
) -> list[CheckpointInfo]:
    """List saved model weights and knowledge checkpoint artifacts."""
    return await run_in_threadpool(engine.list_checkpoints)


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_training(
    payload: EvaluationRequest,
    engine: AIEngineRouter = Depends(get_engine_router),
) -> EvaluationResult:
    """Evaluate intent prediction and trained memory matching for a sample prompt."""
    return await run_in_threadpool(engine.evaluate_training, payload)


@router.post("/reset")
async def reset_training(
    engine: AIEngineRouter = Depends(get_engine_router),
) -> dict[str, object]:
    """Clear persisted checkpoints and reset backend weight caches."""
    return await run_in_threadpool(engine.reset_training)
