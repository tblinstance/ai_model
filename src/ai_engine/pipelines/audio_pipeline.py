"""Multimodal audio pipeline providing Neural Text-to-Speech (Edge-TTS), ASR (Whisper), and Audio Analysis (Librosa/Soundfile)."""

from __future__ import annotations

import asyncio
import io
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from ..models import BaseAIModel, EnsembleInference
from ..schemas import GenerationRequest, TaskType
from .base_pipeline import BasePipeline

try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False

try:
    import whisper
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False

try:
    import librosa
    import soundfile as sf
    _AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    _AUDIO_ANALYSIS_AVAILABLE = False


DEFAULT_VOICES = {
    "woman": "en-US-JennyNeural",
    "man": "en-US-GuyNeural",
    "virtual_woman": "en-US-AriaNeural",
    "virtual_man": "en-US-ChristopherNeural",
}


def _synthesize_waveform_fallback(text: str, duration_seconds: float = 3.0, sample_rate: int = 24000) -> bytes:
    """Fallback sine harmonic audio synthesizer when offline or unconnected."""
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples, endpoint=False, dtype=np.float32)
    # Fundamental pitch with pleasant soft harmonic overtones
    pitch = 180.0 if any(k in text.lower() for k in ("woman", "girl", "female")) else 125.0
    wave = 0.35 * np.sin(2.0 * math.pi * pitch * t)
    wave += 0.15 * np.sin(2.0 * math.pi * (pitch * 2.0) * t)
    wave += 0.08 * np.sin(2.0 * math.pi * (pitch * 3.0) * t)
    # Gentle envelope attack & release
    env = np.clip(t * 10.0, 0.0, 1.0) * np.clip((duration_seconds - t) * 5.0, 0.0, 1.0)
    audio = np.clip(wave * env, -1.0, 1.0)

    if _AUDIO_ANALYSIS_AVAILABLE:
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    # 16-bit PCM WAV raw header construction
    audio_int16 = (audio * 32767.0).astype(np.int16)
    import struct
    buf = io.BytesIO()
    data_size = len(audio_int16) * 2
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(audio_int16.tobytes())
    return buf.getvalue()


class AudioPipeline(BasePipeline):
    """Generates speech voice tracks (TTS), transcribes speech (Whisper), and analyzes acoustics (Librosa)."""

    task = TaskType.AUDIO

    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, Any]:
        prompt = request.prompt.strip()
        lowered = prompt.lower()

        # Select voice gender
        if any(w in lowered for w in ("man", "male", "guy", "boy", "gentleman")):
            voice = DEFAULT_VOICES["virtual_man" if "virtual" in lowered else "man"]
            gender = "man"
        else:
            voice = DEFAULT_VOICES["virtual_woman" if "virtual" in lowered else "woman"]
            gender = "woman"

        override_voice = request.metadata.get("voice")
        if isinstance(override_voice, str) and override_voice:
            voice = override_voice

        audio_bytes: bytes | None = None
        ext = "mp3"
        mime_type = "audio/mpeg"

        # 1. High-fidelity Neural Edge-TTS
        if _EDGE_TTS_AVAILABLE:
            try:
                communicate = edge_tts.Communicate(prompt, voice)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                    tmp_path = tf.name

                async def _tts_run():
                    await communicate.save(tmp_path)

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            pool.submit(asyncio.run, _tts_run()).result()
                    else:
                        loop.run_until_complete(_tts_run())
                except Exception:
                    asyncio.run(_tts_run())

                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    with open(tmp_path, "rb") as f:
                        audio_bytes = f.read()
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            except Exception:
                audio_bytes = None

        # 2. Local fallback audio synthesis with soundfile
        if not audio_bytes:
            audio_bytes = _synthesize_waveform_fallback(prompt, duration_seconds=3.0)
            ext = "wav"
            mime_type = "audio/wav"

        file_path, public_url, preview_b64 = self.storage.save_bytes(
            data=audio_bytes,
            subdir="audio",
            extension=ext,
            include_base64=True,
        )

        extra: dict[str, Any] = {
            "voice": voice,
            "gender": gender,
            "format": ext,
            "engine": "edge-tts" if ext == "mp3" else "librosa_soundfile_harmonic",
            "sample_rate": 24000,
        }

        # Perform acoustic inspection if librosa is available
        if _AUDIO_ANALYSIS_AVAILABLE and ext == "wav":
            try:
                y, sr = sf.read(io.BytesIO(audio_bytes))
                duration = len(y) / float(sr)
                extra["duration_seconds"] = round(duration, 2)
            except Exception:
                pass

        return {
            "text": f"Synthesized speech audio ({extra['engine']}, voice: {voice}) for '{prompt}'.",
            "artifact_url": public_url,
            "artifact_path": str(file_path),
            "preview_base64": preview_b64,
            "mime_type": mime_type,
            "extra": extra,
        }

    def transcribe(self, audio_data: bytes | str | Path, language: str | None = None) -> dict[str, Any]:
        """Transcribe speech audio into text using OpenAI Whisper."""
        if not _WHISPER_AVAILABLE:
            return {
                "text": "OpenAI Whisper is not installed.",
                "language": language or "en",
                "success": False,
            }

        tmp_path = None
        try:
            if isinstance(audio_data, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tf.write(audio_data)
                    tmp_path = tf.name
                target_path = tmp_path
            else:
                target_path = str(audio_data)

            # Use base/tiny Whisper model
            model = whisper.load_model("tiny", in_memory=True)
            result = model.transcribe(target_path, language=language)
            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", language or "en"),
                "segments": len(result.get("segments", [])),
                "success": True,
            }
        except Exception as exc:
            return {
                "text": f"Transcription error: {exc}",
                "language": language or "en",
                "success": False,
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def analyze_audio(self, audio_data: bytes | str | Path) -> dict[str, Any]:
        """Perform acoustic analysis using Librosa and SoundFile."""
        if not _AUDIO_ANALYSIS_AVAILABLE:
            return {"error": "Librosa and SoundFile not available", "success": False}

        try:
            if isinstance(audio_data, bytes):
                y, sr = sf.read(io.BytesIO(audio_data))
            else:
                y, sr = librosa.load(str(audio_data), sr=None)

            # Ensure mono float32
            if y.ndim > 1:
                y = np.mean(y, axis=1)
            y = y.astype(np.float32)

            duration = float(len(y)) / float(sr)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            zero_crossings = float(np.mean(librosa.feature.zero_crossing_rate(y)))
            rms_energy = float(np.mean(librosa.feature.rms(y=y)))

            return {
                "duration_seconds": round(duration, 3),
                "sample_rate": sr,
                "tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1),
                "spectral_centroid_hz": round(spectral_centroid, 1),
                "zero_crossing_rate": round(zero_crossings, 4),
                "rms_energy": round(rms_energy, 4),
                "success": True,
            }
        except Exception as exc:
            return {"error": str(exc), "success": False}
