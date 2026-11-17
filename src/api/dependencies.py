"""Shared FastAPI dependencies and unified inference/quota execution helper."""

from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ai_engine import AIEngineRouter, GenerationRequest, GenerationResponse
from ai_engine.exceptions import AIEngineError
from ai_engine.utils import compute_credit_cost
from .clients import DjangoClient, QuotaDeductionError


def get_engine_router(request: Request) -> AIEngineRouter:
    """Return the singleton AIEngineRouter attached to app state."""
    return request.app.state.engine_router


get_router = get_engine_router


def get_django_client(request: Request) -> DjangoClient:
    """Return the shared async httpx client talking to Django."""
    return request.app.state.django_client


async def run_with_quota(
    request: Request,
    gen_request: GenerationRequest,
    endpoint_path: str,
    authorization: str | None = None,
) -> GenerationResponse:
    """Check/deduct quota if authenticated, run inference, and return output."""
    engine = get_engine_router(request)
    django_client = get_django_client(request)
    estimated_cost = compute_credit_cost(gen_request.tier, gen_request.task)
    resolved_auth = authorization if isinstance(authorization, str) else request.headers.get("authorization")
    resolved_api_key = request.headers.get("x-api-key") or request.headers.get("x-secret-key")

    try:
        # Pre-check & reserve credits before heavy synthesis if token or API key is supplied
        quota_info = await django_client.consume_quota(
            authorization=resolved_auth,
            credits=estimated_cost,
            model_tier=gen_request.tier.value,
            task_type=gen_request.task.value,
            endpoint=endpoint_path,
            api_key=resolved_api_key,
        )
    except QuotaDeductionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    try:
        result = await run_in_threadpool(engine.generate, gen_request)
    except AIEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if quota_info is not None:
        result.extra["quota"] = quota_info
    return result

