"""Code generation endpoints."""

from fastapi import APIRouter, Header, Request

from ai_engine import GenerationRequest, GenerationResponse, TaskType
from ..dependencies import run_with_quota
from ..schemas import CodeRequest

router = APIRouter(prefix="/code", tags=["Code"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_code(
    payload: CodeRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GenerationResponse:
    """Synthesize multi-language source code using neural intent classification."""
    gen_req = GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=TaskType.CODE,
        backend=payload.backend,
        conversation_id=payload.conversation_id,
        messages=payload.messages,
        language=payload.language,
        max_tokens=payload.max_tokens,
        seed=payload.seed,
        metadata=payload.metadata,
    )
    return await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/code/generate",
        authorization=authorization,
    )

