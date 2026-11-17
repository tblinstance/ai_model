"""Audio synthesis, speech transcription (Whisper), and acoustic analysis (Librosa/Soundfile) endpoints."""

from __future__ import annotations

import base64
from typing import Any
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ai_engine import GenerationRequest, GenerationResponse, TaskType
from ..dependencies import get_router, run_with_quota
from ..schemas import ChatRequest

router = APIRouter(prefix="/audio", tags=["Audio"])


class AudioTranscribeRequest(BaseModel):
    audio_base64: str | None = Field(default=None, description="Base64 encoded audio bytes")
    audio_path: str | None = Field(default=None, description="Path to audio file on disk")
    language: str | None = Field(default=None, description="Target language code (e.g. 'en')")


class AudioAnalyzeRequest(BaseModel):
    audio_base64: str | None = Field(default=None, description="Base64 encoded audio bytes")
    audio_path: str | None = Field(default=None, description="Path to audio file on disk")


@router.post("/generate", response_model=GenerationResponse)
async def generate_audio(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GenerationResponse:
    """Generate high-fidelity speech audio (Edge-TTS or neural waveform) from text prompt."""
    gen_req = GenerationRequest(
        prompt=payload.prompt,
        tier=payload.tier,
        task=TaskType.AUDIO,
        backend=payload.backend,
        metadata={"voice": payload.metadata.get("voice") if payload.metadata else None},
    )
    return await run_with_quota(
        request=request,
        gen_request=gen_req,
        endpoint_path="/api/v1/audio/generate",
        authorization=authorization,
    )


@router.post("/transcribe")
async def transcribe_audio(payload: AudioTranscribeRequest, request: Request) -> dict[str, Any]:
    """Transcribe speech audio into text using OpenAI Whisper."""
    ai_router = get_router(request)
    audio_data = None
    if payload.audio_base64:
        try:
            audio_data = base64.b64decode(payload.audio_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid audio_base64 data.")
    elif payload.audio_path:
        audio_data = payload.audio_path
    else:
        raise HTTPException(status_code=400, detail="Either audio_base64 or audio_path is required.")

    return ai_router.transcribe_audio(audio_data, language=payload.language)


@router.post("/analyze")
async def analyze_audio(payload: AudioAnalyzeRequest, request: Request) -> dict[str, Any]:
    """Perform acoustic analysis (tempo, pitch, energy, spectral centroid) with Librosa & Soundfile."""
    ai_router = get_router(request)
    audio_data = None
    if payload.audio_base64:
        try:
            audio_data = base64.b64decode(payload.audio_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid audio_base64 data.")
    elif payload.audio_path:
        audio_data = payload.audio_path
    else:
        raise HTTPException(status_code=400, detail="Either audio_base64 or audio_path is required.")

    return ai_router.analyze_audio(audio_data)
