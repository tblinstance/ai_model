"""Image synthesis endpoints."""

from fastapi import APIRouter, Header, Request

from ai_engine import GenerationRequest, GenerationResponse, TaskType
from ..dependencies import run_with_quota
from ..schemas import ImageRequest

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(
    payload: ImageRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GenerationResponse:
    """Generate a PNG image from neural spatial fields."""
    gen_req = GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=TaskType.IMAGES,
        backend=payload.backend,
        width=payload.width,
        height=payload.height,
        seed=payload.seed,
        metadata=payload.metadata,
    )
    return await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/images/generate",
        authorization=authorization,
    )

