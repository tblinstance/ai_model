"""Video generation endpoints."""

from fastapi import APIRouter, Header, Request

from ai_engine import GenerationRequest, GenerationResponse, TaskType
from ..dependencies import run_with_quota
from ..schemas import VideoRequest

router = APIRouter(prefix="/video", tags=["Video"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_video(
    payload: VideoRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GenerationResponse:
    """Synthesize a minimum 10-minute H.264 MP4 video sequence."""
    gen_req = GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=TaskType.VIDEO,
        backend=payload.backend,
        width=payload.width,
        height=payload.height,
        frames=payload.frames,
        duration_seconds=payload.duration_seconds,
        seed=payload.seed,
        metadata=payload.metadata,
    )
    return await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/video/generate",
        authorization=authorization,
    )

