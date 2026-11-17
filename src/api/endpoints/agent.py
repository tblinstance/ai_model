"""Autonomous agent execution endpoint selecting task modalities dynamically."""

from fastapi import APIRouter, Header, Request

from ai_engine import GenerationRequest, TaskType
from ..dependencies import run_with_quota
from ..schemas import AgentRunRequest, AgentRunResponse

router = APIRouter(prefix="/agent", tags=["Agent"])


def _infer_task(prompt: str, explicit: TaskType | None) -> TaskType:
    if explicit is not None:
        return explicit
    lowered = prompt.lower()
    if any(k in lowered for k in ("video", "animation", "clip", "motion frame")):
        return TaskType.VIDEO
    if any(
        k in lowered
        for k in (
            "image",
            "picture",
            "render",
            "illustration",
            "poster",
            "draw",
            "paint",
            "sketch",
            "portrait",
        )
    ):
        return TaskType.IMAGES
    if any(k in lowered for k in ("code", "function", "script", "python", "typescript", "sql")):
        return TaskType.CODE
    return TaskType.CHAT


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    payload: AgentRunRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> AgentRunResponse:
    """Resolve best modality for the agent prompt and execute inference."""
    resolved_task = _infer_task(payload.prompt, payload.task)
    gen_req = GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=resolved_task,
        backend=payload.backend,
        conversation_id=payload.conversation_id,
        messages=payload.messages,
        system_prompt=payload.system_prompt or f"Agent persona: {payload.agent_name}",
    )
    result = await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/agent/run",
        authorization=authorization,
    )
    return AgentRunResponse(
        agent_name=payload.agent_name,
        resolved_task=resolved_task,
        result=result,
    )

