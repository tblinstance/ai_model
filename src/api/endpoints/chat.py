"""Chat and SSE streaming endpoints."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from ai_engine import AIEngineRouter, GenerationRequest, GenerationResponse, TaskType
from ..dependencies import get_engine_router, run_with_quota
from ..schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


def _build_chat_request(payload: ChatRequest) -> GenerationRequest:
    return GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=TaskType.CHAT,
        backend=payload.backend,
        conversation_id=payload.conversation_id,
        messages=payload.messages,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        seed=payload.seed,
        metadata=payload.metadata,
    )


@router.post("", response_model=GenerationResponse)
async def generate_chat(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GenerationResponse:
    """Generate a chat response using the selected Flash, Pro, or Advance tier."""
    gen_req = _build_chat_request(payload)
    return await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/chat",
        authorization=authorization,
    )


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    engine: AIEngineRouter = Depends(get_engine_router),
) -> StreamingResponse:
    """Stream chat completion chunks over Server-Sent Events."""
    gen_req = _build_chat_request(payload)

    def event_stream():
        for chunk in engine.stream_chat(gen_req):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

