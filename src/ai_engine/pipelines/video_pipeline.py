"""Video synthesis pipeline creating H.264 MP4 sequences (10+ minute minimum) via NumPy + FFmpeg."""

from __future__ import annotations

import base64
import math
import re
import tempfile
from pathlib import Path

import numpy as np

from ..models import BaseAIModel, EnsembleInference
from ..schemas import GenerationRequest, ModelTier, TaskType
from .base_pipeline import BasePipeline
from .media_renderer import (
    MIN_VIDEO_DURATION_SECONDS,
    apply_colormap_with_lut,
    array_to_image,
    decode_reference_frames,
    encode_image,
    encode_mp4_sequence,
    get_prompt_colormap_lut,
    parse_video_duration_seconds,
    pillow_capabilities,
)
from .photorealistic_portrait import render_photorealistic_portrait

_TIER_VIDEO_DIMS: dict[ModelTier, tuple[int, int]] = {
    ModelTier.FLASH: (320, 240),
    ModelTier.PRO: (384, 288),
    ModelTier.ADVANCE: (480, 360),
}


def _select_motion_mode(prompt: str) -> str:
    lowered = prompt.lower()
    if any(k in lowered for k in ("trump", "donald", "donail", "dunal", "donalt", "tum", "trum", "caricature", "parody")):
        return "trump"
    if any(k in lowered for k in ("cartoon", "carton", "anime", "toon", "cel", "comic", "popart")):
        return "cartoon"
    if any(
        k in lowered
        for k in (
            "man", "woman", "person", "human", "face", "portrait", "girl",
            "boy", "guy", "lady", "female", "male", "character", "actor",
            "actress", "model", "people", "speaking", "talking", "interview",
        )
    ):
        return "human"
    if any(k in lowered for k in ("ripple", "pulse", "sonar", "tidal")):
        return "ripple"
    if any(k in lowered for k in ("spiral", "vortex", "cosmos", "nebula")):
        return "vortex"
    if any(k in lowered for k in ("sweep", "grid", "radar", "matrix")):
        return "sweep"
    return "orbit"


def _even_dim(value: int, min_val: int = 64, max_val: int = 1280) -> int:
    clamped = max(min_val, min(max_val, int(value)))
    return clamped if clamped % 2 == 0 else clamped - 1


def _format_duration_label(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins:02d}m {secs:02d}s"
    return f"{mins}m {secs:02d}s"


class VideoPipeline(BasePipeline):
    """Synthesizes long-form (>= 10 min) H.264 MP4 motion sequences from neural spatial fields."""

    task = TaskType.VIDEO

    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object]:
        res_match = re.search(r"\b(\d{3,4})x(\d{3,4})\b", request.prompt.lower())
        prompt_w = int(res_match.group(1)) if res_match else None
        prompt_h = int(res_match.group(2)) if res_match else None

        fps_match = re.search(r"\b(\d{1,2})\s*fps\b", request.prompt.lower())
        prompt_fps = int(fps_match.group(1)) if fps_match else None

        default_w, default_h = _TIER_VIDEO_DIMS.get(model.spec.tier, (320, 240))
        width = _even_dim(request.width or prompt_w or default_w, max_val=1280)
        height = _even_dim(request.height or prompt_h or default_h, max_val=720)
        fps = max(12, min(24, int(prompt_fps or model.spec.video_fps)))

        target_duration = parse_video_duration_seconds(request.prompt, request.duration_seconds)
        # 15s divides 600s, 720s, 900s, 1200s, 1800s, 3600s cleanly so loops avoid GOP mid-cuts
        cycle_seconds = 15
        cycle_frames = fps * cycle_seconds

        field_a, used_backends = model.synthesize_spatial(
            prompt=request.prompt,
            width=width,
            height=height,
            backend_override=request.backend,
            seed=request.seed,
        )
        field_b, _ = model.synthesize_spatial(
            prompt=request.prompt + " :: keyframe_b",
            width=width,
            height=height,
            backend_override=request.backend,
            seed=(request.seed or 17) + 99,
        )
        field_c = np.clip(
            0.55 * np.flip(field_a, axis=1) + 0.45 * np.roll(field_b, shift=max(1, width // 4), axis=1),
            0.0,
            1.0,
        ).astype(np.float32)

        ref_frames_raw = request.metadata.get("reference_frames_base64")
        ref_single_raw = request.metadata.get("reference_image_base64")
        ref_frames, ref_meta = decode_reference_frames(
            ref_frames_raw if isinstance(ref_frames_raw, list) else None,
            str(ref_single_raw) if ref_single_raw else None,
            width=width,
            height=height,
        )

        # Build ping-pong reference list so multi-frame uploads loop seamlessly without jump cuts
        loop_refs: list[np.ndarray] = []
        if len(ref_frames) >= 2:
            loop_refs = ref_frames + list(reversed(ref_frames[1:-1]))
            if len(loop_refs) == 2:
                loop_refs = [ref_frames[0], ref_frames[1], ref_frames[0]]
        elif len(ref_frames) == 1:
            loop_refs = [ref_frames[0]]

        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        xx_norm = (xx / max(1, width - 1)) * 2.0 - 1.0
        yy_norm = (yy / max(1, height - 1)) * 2.0 - 1.0
        radial = np.sqrt(xx_norm * xx_norm + yy_norm * yy_norm)
        angle = np.arctan2(yy_norm, xx_norm)
        orb_radius2 = float(max(12, min(width, height) // 9) ** 2)
        orb_tint = np.array([1.0, 0.98, 0.94], dtype=np.float32)

        lowered_prompt = request.prompt.lower()
        motion_mode = _select_motion_mode(request.prompt)
        lut, cmap_used = get_prompt_colormap_lut(request.prompt)
        if motion_mode in ("human", "trump") and not any(k in lowered_prompt for k in ("neon", "cyber", "plasma", "inferno", "matrix")):
            lut = None
            cmap_used = "natural_portrait"
        elif lut is None:
            cmap_used = "rgb"

        poster_holder: list[np.ndarray] = []

        def _iter_cycle_frames():
            for frame_idx in range(cycle_frames):
                phase = (frame_idx / float(cycle_frames)) * 2.0 * math.pi
                # Three smooth harmonic weights summing to 1.0 across the full [0, 2pi) cycle
                w_a = (1.0 + math.cos(phase)) / 3.0
                w_b = (1.0 + math.cos(phase - (2.0 * math.pi / 3.0))) / 3.0
                w_c = max(0.0, 1.0 - w_a - w_b)

                if motion_mode == "cartoon":
                    # Playful 2D bouncy harmonic wave with cross-axis motion
                    wave = 0.18 * np.sin(xx_norm * 4.0 + phase * 2.5) * np.cos(yy_norm * 3.5 - phase * 2.0)
                elif motion_mode == "trump":
                    # Comedic speech oratory harmonics, dramatic head tilt, and signature accordion hand sway
                    wave = 0.03 * np.sin(phase * 3.0) * np.cos(xx_norm * 2.5) + 0.015 * np.cos(phase * 1.5)
                elif motion_mode == "human":
                    # Physiological breathing & subtle head micro-sway for realistic human motion
                    breath = 0.02 * np.sin(phase) * np.clip((yy_norm + 0.3) * 1.5, 0.0, 1.0)
                    sway = 0.012 * np.cos(phase * 0.5) * np.exp(-(radial ** 2) * 1.5)
                    wave = breath + sway
                elif motion_mode == "ripple":
                    wave = 0.16 * np.sin(radial * 7.5 - phase * 2.0)
                elif motion_mode == "vortex":
                    wave = 0.16 * np.sin(radial * 5.0 + angle * 2.0 - phase)
                elif motion_mode == "sweep":
                    wave = 0.14 * np.sin(xx_norm * 4.0 + phase * 2.0) * np.cos(yy_norm * 3.0)
                else:
                    wave = 0.14 * np.sin(xx_norm * 3.0 + phase) * np.cos(yy_norm * 2.5 - phase)

                neural_mix = (
                    (field_a * w_a)
                    + (field_b * w_b)
                    + (field_c * w_c)
                    + wave[..., None]
                )

                if loop_refs:
                    if len(loop_refs) >= 2:
                        pos = (frame_idx / float(cycle_frames)) * len(loop_refs)
                        lo = int(math.floor(pos)) % len(loop_refs)
                        hi = (lo + 1) % len(loop_refs)
                        alpha = pos - math.floor(pos)
                        base_ref = loop_refs[lo] * (1.0 - alpha) + loop_refs[hi] * alpha
                    elif motion_mode in ("human", "trump"):
                        # Photorealistic breathing and subtle facial micro-motion for real human portraits
                        shift_y = int(round(2.0 * math.sin(phase)))
                        shift_x = int(round(1.5 * math.cos(phase * 0.5)))
                        shifted = np.roll(np.roll(loop_refs[0], shift=shift_y, axis=0), shift=shift_x, axis=1)
                        base_ref = loop_refs[0] * 0.88 + shifted * 0.12
                    else:
                        shift_px = int(round(6.0 * math.sin(phase)))
                        shifted = np.roll(loop_refs[0], shift=shift_px, axis=1)
                        base_ref = loop_refs[0] * 0.72 + shifted * 0.28

                    if motion_mode in ("human", "trump"):
                        # High 94% photo fidelity to preserve real face, eyes, hair, and skin tones
                        frame_arr = np.clip(base_ref * 0.94 + neural_mix * 0.06, 0.0, 1.0)
                        tint_weight = 0.0
                    else:
                        frame_arr = np.clip(base_ref * 0.72 + neural_mix * 0.28, 0.0, 1.0)
                        tint_weight = 0.24
                elif motion_mode in ("human", "trump"):
                    if motion_mode == "trump":
                        is_realistic = any(w in lowered_prompt for w in ("realistic", "real", "realstic", "photo", "photorealistic", "hd", "portrait"))
                        is_caricature = any(w in lowered_prompt for w in ("caricature", "parody", "funny", "comedy", "cartoon", "satire", "satirical", "meme", "flash"))
                        if is_caricature and not is_realistic:
                            gender_key = "trump_caricature"
                        elif is_realistic:
                            gender_key = "trump"
                        else:
                            gender_key = "trump_caricature" if ("funny" in lowered_prompt or "comedy" in lowered_prompt) else "trump"
                        blink_val = 1.0 if (frame_idx % cycle_frames in (0, 1, 2)) else 0.0
                        mouth_open_val = max(0.0, 0.65 * math.sin(phase * 3.5) + 0.35 * math.cos(phase * 7.0))
                        sway_x_val = 0.024 * math.sin(phase * 1.4)  # Animated comedic head tilt
                        sway_y_val = 0.014 * math.cos(phase * 1.0)
                        breath_y_val = 0.018 * math.sin(phase)
                    else:
                        # Determine gender persona from user prompt
                        if any(w in lowered_prompt for w in ("man", "boy", "guy", "male", "gentleman")):
                            gender_key = "virtual_man" if "virtual" in lowered_prompt else "man"
                        else:
                            gender_key = "virtual_woman" if "virtual" in lowered_prompt else "woman"

                        blink_val = 1.0 if (frame_idx % cycle_frames in (0, 1, 2)) else 0.0
                        mouth_open_val = max(0.0, 0.55 * math.sin(phase * 3.5) + 0.25 * math.cos(phase * 7.0))
                        sway_x_val = 0.012 * math.sin(phase * 0.7)
                        sway_y_val = 0.008 * math.cos(phase * 0.5)
                        breath_y_val = 0.015 * math.sin(phase)

                    portrait_frame = render_photorealistic_portrait(
                        width=width,
                        height=height,
                        gender=gender_key,
                        phase=phase,
                        mouth_open=mouth_open_val,
                        blink=blink_val,
                        sway_x=sway_x_val,
                        sway_y=sway_y_val,
                        breath_y=breath_y_val,
                    )
                    # Blend with subtle neural spatial field texture (5%)
                    frame_arr = np.clip(portrait_frame * 0.95 + neural_mix * 0.05, 0.0, 1.0)
                    tint_weight = 0.0
                else:
                    frame_arr = np.clip(neural_mix, 0.0, 1.0)
                    tint_weight = 0.42

                if motion_mode == "cartoon":
                    # Discrete cel-shading quantization (4-6 distinct ink tonal levels)
                    frame_arr = np.round(frame_arr * 5.0) / 5.0

                colored = apply_colormap_with_lut(frame_arr, lut, tint_strength=tint_weight)
                colored = np.clip((colored - 0.5) * 1.08 + 0.5, 0.0, 1.0)

                if motion_mode == "human":
                    # Cinematic studio portrait vignette without glowing sci-fi orb
                    vignette = np.clip(1.0 - 0.20 * (radial ** 2), 0.78, 1.0)
                    composited = np.clip(colored * vignette[..., None], 0.0, 1.0)
                else:
                    orb_x = width * (0.5 + 0.28 * math.cos(phase))
                    orb_y = height * (0.5 + 0.22 * math.sin(phase * 2.0))
                    glow = 0.30 * np.exp(-(((xx - orb_x) ** 2) + ((yy - orb_y) ** 2)) / (2.0 * orb_radius2))
                    composited = np.clip(colored * (1.0 - glow[..., None]) + orb_tint * glow[..., None], 0.0, 1.0)

                if frame_idx == 0:
                    poster_holder.append(composited.copy())

                yield np.clip(composited * 255.0, 0.0, 255.0).astype(np.uint8)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_mp4 = Path(tmp_dir) / "rendered.mp4"
            encode_stats = encode_mp4_sequence(
                frames=_iter_cycle_frames(),
                width=width,
                height=height,
                fps=fps,
                duration_seconds=target_duration,
                output_path=temp_mp4,
            )
            file_path, public_url = self.storage.save_file(
                source_path=temp_mp4,
                subdir="video",
                extension="mp4",
            )

        poster_data_url: str | None = None
        if poster_holder:
            poster_bytes, _, _ = encode_image(array_to_image(poster_holder[0]), output_format="JPEG", quality=78)
            poster_data_url = f"data:image/jpeg;base64,{base64.b64encode(poster_bytes).decode('ascii')}"

        trained_preset = None
        if self.trainer is not None:
            matched, match_score = self.trainer.retrieve_best_match(
                request.prompt,
                task=TaskType.VIDEO,
                min_score=0.52,
            )
            if matched is not None:
                trained_preset = {"score": match_score, "preset": matched.response}

        caps = pillow_capabilities()
        extra: dict[str, object] = {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": encode_stats["duration_seconds"],
            "minimum_duration_seconds": MIN_VIDEO_DURATION_SECONDS,
            "requested_duration_seconds": request.duration_seconds,
            "total_frames": encode_stats["total_frames"],
            "cycle_seconds": encode_stats["cycle_seconds"],
            "cycle_frames": encode_stats["cycle_frames"],
            "loop_repeats": encode_stats["loop_repeats"],
            "codec": encode_stats["codec"],
            "container": encode_stats["container"],
            "pixel_format": encode_stats["pixel_format"],
            "file_size_bytes": encode_stats["file_size_bytes"],
            "file_size_mb": encode_stats["file_size_mb"],
            "motion_mode": motion_mode,
            "colormap": cmap_used,
            "renderer": "ffmpeg+numpy",
            "ffmpeg_binary": encode_stats["ffmpeg_binary"],
            "pillow_version": caps["version"],
            "conditioned_on_upload": bool(ref_frames),
            "uploaded_keyframes": len(ref_frames),
        }
        if poster_data_url:
            extra["poster_data_url"] = poster_data_url
        if ref_meta:
            extra["reference_info"] = ref_meta[0]
        if trained_preset is not None:
            extra["trained_preset"] = trained_preset

        source_note = f" from uploaded {len(ref_frames)}-frame media" if ref_frames else ""
        dur_label = _format_duration_label(int(encode_stats["duration_seconds"]))
        return {
            "text": (
                f"Synthesized {dur_label} ({encode_stats['duration_seconds']}s, {encode_stats['total_frames']:,} frames) "
                f"H.264 MP4 {motion_mode} video{source_note} ({width}x{height} @ {fps} FPS, {cmap_used}, "
                f"{encode_stats['file_size_mb']} MB)."
            ),
            "artifact_url": public_url,
            "artifact_path": str(file_path),
            "preview_base64": None,
            "mime_type": "video/mp4",
            "extra": extra,
        }

