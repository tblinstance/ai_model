"""Shared Pillow + Matplotlib + NumPy media rendering utilities for Images and Video pipelines."""

from __future__ import annotations

import base64
from collections.abc import Iterable
import hashlib
import io
import math
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageSequence, features

try:
    import matplotlib
except ImportError:  # pragma: no cover
    matplotlib = None  # type: ignore[assignment]

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None  # type: ignore[assignment]

try:
    import scipy.ndimage as ndi
except ImportError:  # pragma: no cover
    ndi = None

try:
    import skimage
    import skimage.filters as sk_filters
except ImportError:  # pragma: no cover
    skimage = None
    sk_filters = None

MIN_VIDEO_DURATION_SECONDS = 600
MAX_VIDEO_DURATION_SECONDS = 3600

_FORMAT_MAP: dict[str, tuple[str, str, str]] = {
    "png": ("PNG", "png", "image/png"),
    "webp": ("WEBP", "webp", "image/webp"),
    "jpg": ("JPEG", "jpg", "image/jpeg"),
    "jpeg": ("JPEG", "jpg", "image/jpeg"),
}

_PROMPT_COLORMAP_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("cyberpunk", "neon", "synthwave", "magenta", "purple", "violet"), "plasma"),
    (("sunset", "fire", "lava", "ember", "warm", "golden", "amber"), "inferno"),
    (("ocean", "water", "coral", "sea", "teal", "bioluminescen"), "viridis"),
    (("aurora", "cosmos", "cosmic", "nebula", "galaxy", "starlight"), "twilight_shifted"),
    (("forest", "emerald", "botanical", "green", "jungle", "fern"), "YlGn"),
    (("arctic", "glacier", "ice", "winter", "frost", "snow"), "PuBu"),
    (("monochrome", "obsidian", "grayscale", "charcoal", "silver"), "Greys_r"),
    (("cartoon", "carton", "anime", "comic", "popart", "toon", "cel", "vibrant"), "tab10"),
)

_FALLBACK_COLORMAPS: tuple[str, ...] = ("turbo", "viridis", "plasma", "magma", "cividis")


def resolve_ffmpeg_executable() -> str | None:
    """Locate system ffmpeg or bundled imageio-ffmpeg binary for H.264 MP4 synthesis."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    if imageio_ffmpeg is not None:
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and Path(exe).exists():
                return exe
        except Exception:
            return None
    return None


def parse_video_duration_seconds(prompt: str, requested_seconds: int | None = None) -> int:
    """Resolve target MP4 duration in seconds, enforcing a 10-minute (600s) minimum."""
    candidate = int(requested_seconds) if requested_seconds is not None else None
    if candidate is None and prompt:
        lowered = prompt.lower()
        hr_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b", lowered)
        min_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b", lowered)
        sec_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?)\b", lowered)
        if hr_match:
            candidate = round(float(hr_match.group(1)) * 3600)
        elif min_match:
            candidate = round(float(min_match.group(1)) * 60)
        elif sec_match:
            candidate = round(float(sec_match.group(1)))
    effective = candidate if candidate is not None else MIN_VIDEO_DURATION_SECONDS
    return max(MIN_VIDEO_DURATION_SECONDS, min(MAX_VIDEO_DURATION_SECONDS, effective))


def pillow_capabilities() -> dict[str, Any]:
    """Return installed Pillow, Matplotlib, and FFmpeg MP4 media rendering capabilities."""
    png_ok = bool(features.check("zlib"))
    webp_ok = bool(features.check("webp"))
    jpeg_ok = bool(features.check("jpg"))
    ffmpeg_exe = resolve_ffmpeg_executable()
    info: dict[str, Any] = {
        "engine": "pillow",
        "version": Image.__version__,
        "codecs": {
            "png": png_ok,
            "gif": True,
            "webp": webp_ok,
            "jpeg": jpeg_ok,
            "mp4": bool(ffmpeg_exe),
        },
        "text_shaping": {
            "freetype2": bool(features.check("freetype2")),
            "raqm": bool(features.check("raqm")),
        },
        "video_mp4": {
            "engine": "ffmpeg",
            "available": bool(ffmpeg_exe),
            "binary": Path(ffmpeg_exe).name if ffmpeg_exe else None,
            "minimum_duration_seconds": MIN_VIDEO_DURATION_SECONDS,
            "max_duration_seconds": MAX_VIDEO_DURATION_SECONDS,
        },
    }
    if matplotlib is not None:
        info["colormaps"] = {
            "engine": "matplotlib",
            "version": matplotlib.__version__,
        }
    if ndi is not None:
        import scipy
        info["scipy"] = {
            "available": True,
            "version": getattr(scipy, "__version__", "installed"),
            "ndimage": True,
        }
    if skimage is not None:
        info["scikit_image"] = {
            "available": True,
            "version": getattr(skimage, "__version__", "installed"),
        }
    return info


def select_colormap(prompt: str) -> str:
    """Choose a prompt-matched Matplotlib perceptual colormap deterministically."""
    lowered = prompt.lower()
    for cues, cmap_name in _PROMPT_COLORMAP_RULES:
        if any(cue in lowered for cue in cues):
            return cmap_name
    idx = hashlib.sha256(prompt.encode("utf-8")).digest()[0] % len(_FALLBACK_COLORMAPS)
    return _FALLBACK_COLORMAPS[idx]


@lru_cache(maxsize=16)
def _colormap_lut(cmap_name: str) -> np.ndarray | None:
    if matplotlib is None:
        return None
    try:
        cmap = matplotlib.colormaps.get_cmap(cmap_name)
    except Exception:
        return None
    samples = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    rgba = np.asarray(cmap(samples), dtype=np.float32)
    return np.clip(rgba[:, :3], 0.0, 1.0)


def get_prompt_colormap_lut(prompt: str) -> tuple[np.ndarray | None, str]:
    """Return precomputed Matplotlib RGB LUT and resolved colormap name for a prompt."""
    cmap_name = select_colormap(prompt)
    return _colormap_lut(cmap_name), cmap_name


def apply_colormap_with_lut(
    spatial: np.ndarray,
    lut: np.ndarray | None,
    tint_strength: float = 0.48,
) -> np.ndarray:
    """Blend normalized RGB float32 fields with a pre-fetched Matplotlib RGB LUT."""
    if lut is None:
        return np.clip(spatial, 0.0, 1.0).astype(np.float32)
    luma = spatial.mean(axis=2)
    indices = np.clip((luma * 255.0).astype(np.int32), 0, 255)
    mapped = lut[indices]
    blended = spatial * (1.0 - tint_strength) + mapped * tint_strength
    return np.clip(blended, 0.0, 1.0).astype(np.float32)


def apply_prompt_colormap(
    spatial: np.ndarray,
    prompt: str,
    tint_strength: float = 0.48,
) -> tuple[np.ndarray, str]:
    """Blend neural spatial RGB fields with a perceptual Matplotlib LUT matching prompt tone."""
    lut, cmap_name = get_prompt_colormap_lut(prompt)
    if lut is None:
        return apply_colormap_with_lut(spatial, None, tint_strength=tint_strength), "rgb"
    return apply_colormap_with_lut(spatial, lut, tint_strength=tint_strength), cmap_name


def array_to_image(rgb_float: np.ndarray, smooth: bool = False) -> Image.Image:
    """Convert normalized [0, 1] float32 (H, W, 3) array into a Pillow RGB Image with SciPy filtering."""
    if smooth and ndi is not None:
        rgb_float = ndi.gaussian_filter(rgb_float, sigma=(0.75, 0.75, 0.0))
    clipped = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    image = Image.fromarray(clipped, mode="RGB")
    if smooth and ndi is None:
        image = image.filter(ImageFilter.SMOOTH_MORE)
    return image


def enhance_image(
    image: Image.Image,
    contrast: float = 1.08,
    color: float = 1.12,
    sharpness: float = 1.06,
) -> Image.Image:
    """Apply gentle Pillow contrast, saturation, and sharpness tuning."""
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    if color != 1.0:
        image = ImageEnhance.Color(image).enhance(color)
    if sharpness != 1.0:
        image = ImageEnhance.Sharpness(image).enhance(sharpness)
    return image


def encode_image(
    image: Image.Image,
    output_format: str = "PNG",
    quality: int = 92,
) -> tuple[bytes, str, str]:
    """Encode a Pillow Image into bytes, returning (bytes, file_ext, mime_type)."""
    fmt_key = (output_format or "png").strip().lower()
    pil_fmt, ext, mime = _FORMAT_MAP.get(fmt_key, _FORMAT_MAP["png"])
    if pil_fmt == "WEBP" and not features.check("webp"):
        pil_fmt, ext, mime = _FORMAT_MAP["png"]
    elif pil_fmt == "JPEG" and not features.check("jpg"):
        pil_fmt, ext, mime = _FORMAT_MAP["png"]

    buf = io.BytesIO()
    if pil_fmt == "PNG":
        image.save(buf, format="PNG", optimize=True)
    elif pil_fmt == "WEBP":
        image.save(buf, format="WEBP", quality=quality, method=4)
    else:
        image.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), ext, mime


def quantize_gif_frame(frame: Image.Image, colors: int = 128) -> Image.Image:
    """Quantize an RGB Pillow image to an indexed palette rapidly using FastOctree."""
    try:
        return frame.quantize(
            colors=colors,
            method=Image.Quantize.FASTOCTREE,
            dither=Image.Dither.NONE,
        )
    except Exception:
        return frame.convert("P", palette=Image.Palette.ADAPTIVE)


def decode_reference_image(
    raw_b64: str,
    target_size: tuple[int, int] | None = None,
) -> tuple[np.ndarray, dict[str, Any]] | None:
    """Decode base64 / data-URL image bytes via Pillow into normalized float32 RGB + telemetry."""
    if not raw_b64 or not isinstance(raw_b64, str):
        return None
    payload = raw_b64.split(",", 1)[1] if raw_b64.startswith("data:") and "," in raw_b64 else raw_b64
    payload = payload.strip()
    if not payload:
        return None
    try:
        raw_bytes = base64.b64decode(payload, validate=False)
    except Exception:
        return None
    if not raw_bytes or len(raw_bytes) > 15 * 1024 * 1024:
        return None

    try:
        with Image.open(io.BytesIO(raw_bytes)) as opened:
            fmt = (opened.format or "PNG").upper()
            orig_w, orig_h = opened.size
            img = ImageOps.exif_transpose(opened).convert("RGB")
            if target_size is not None:
                img = ImageOps.fit(
                    img,
                    target_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
            arr = np.asarray(img, dtype=np.float32) / 255.0
    except Exception:
        return None

    mean_rgb = arr.mean(axis=(0, 1))
    r_u8, g_u8, b_u8 = (int(np.clip(c * 255.0, 0, 255)) for c in mean_rgb.tolist())
    stats: dict[str, Any] = {
        "orig_width": orig_w,
        "orig_height": orig_h,
        "source_format": fmt,
        "brightness": round(float(mean_rgb.mean()), 3),
        "dominant_hex": f"#{r_u8:02x}{g_u8:02x}{b_u8:02x}",
    }
    return np.clip(arr, 0.0, 1.0).astype(np.float32), stats


def decode_reference_frames(
    frames_b64: list[str] | None,
    single_b64: str | None,
    width: int,
    height: int,
    max_frames: int = 8,
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    """Decode uploaded video keyframes or animated GIF sequence into resized RGB float32 arrays."""
    decoded: list[np.ndarray] = []
    meta_list: list[dict[str, Any]] = []

    if frames_b64:
        for item in frames_b64[:max_frames]:
            res = decode_reference_image(item, target_size=(width, height))
            if res is not None:
                decoded.append(res[0])
                meta_list.append(res[1])
        if decoded:
            return decoded, meta_list

    if not single_b64:
        return [], []

    payload = single_b64.split(",", 1)[1] if single_b64.startswith("data:") and "," in single_b64 else single_b64
    try:
        raw_bytes = base64.b64decode(payload.strip(), validate=False)
        with Image.open(io.BytesIO(raw_bytes)) as opened:
            orig_w, orig_h = opened.size
            fmt = (opened.format or "IMAGE").upper()
            for frame_idx, raw_frame in enumerate(ImageSequence.Iterator(opened)):
                if frame_idx >= max_frames:
                    break
                rgb_frame = ImageOps.fit(
                    raw_frame.convert("RGB"),
                    (width, height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                arr = np.clip(np.asarray(rgb_frame, dtype=np.float32) / 255.0, 0.0, 1.0).astype(np.float32)
                mean_rgb = arr.mean(axis=(0, 1))
                r_u8, g_u8, b_u8 = (int(np.clip(c * 255.0, 0, 255)) for c in mean_rgb.tolist())
                decoded.append(arr)
                meta_list.append(
                    {
                        "orig_width": orig_w,
                        "orig_height": orig_h,
                        "source_format": fmt,
                        "brightness": round(float(mean_rgb.mean()), 3),
                        "dominant_hex": f"#{r_u8:02x}{g_u8:02x}{b_u8:02x}",
                    }
                )
    except Exception:
        pass
    return decoded, meta_list


def encode_gif(frames: list[Image.Image], fps: int) -> bytes:
    """Quantize and encode RGB Pillow frames into a looping animated GIF."""
    if not frames:
        raise ValueError("GIF encoding requires at least one frame.")
    paletted = [quantize_gif_frame(frame) for frame in frames]
    duration_ms = max(20, int(1000 / max(1, fps)))
    buf = io.BytesIO()
    paletted[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=paletted[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return buf.getvalue()


def encode_mp4_sequence(
    frames: Iterable[np.ndarray],
    width: int,
    height: int,
    fps: int,
    duration_seconds: int,
    output_path: Path,
) -> dict[str, Any]:
    """Stream RGB24 NumPy frames to FFmpeg (H.264 Main/yuv420p) and extend to target duration."""
    ffmpeg_exe = resolve_ffmpeg_executable()
    if not ffmpeg_exe:
        raise RuntimeError(
            "No FFmpeg binary found for MP4 generation. Install 'imageio-ffmpeg' or system 'ffmpeg'."
        )
    if width % 2 != 0 or height % 2 != 0:
        raise ValueError(f"MP4 encoding requires even dimensions; got {width}x{height}.")

    safe_fps = max(1, int(fps))
    target_duration = max(MIN_VIDEO_DURATION_SECONDS, min(MAX_VIDEO_DURATION_SECONDS, int(duration_seconds)))

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        cycle_mp4 = tmp_dir / "cycle.mp4"
        concat_txt = tmp_dir / "concat.txt"

        encode_cmd = [
            ffmpeg_exe,
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(safe_fps),
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "animation",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "main",
            "-g",
            str(safe_fps),
            "-keyint_min",
            str(safe_fps),
            "-sc_threshold",
            "0",
            str(cycle_mp4),
        ]
        proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frame_count = 0
        try:
            assert proc.stdin is not None
            for frame_rgb in frames:
                arr = np.asarray(frame_rgb, dtype=np.uint8)
                if arr.shape != (height, width, 3):
                    raise ValueError(
                        f"Expected RGB24 frame shape {(height, width, 3)}, got {arr.shape}."
                    )
                proc.stdin.write(np.ascontiguousarray(arr).tobytes())
                frame_count += 1
        finally:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()

        stderr_encode = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        rc_encode = proc.wait()
        if rc_encode != 0 or frame_count == 0 or not cycle_mp4.exists():
            raise RuntimeError(f"FFmpeg H.264 encode failed (rc={rc_encode}, frames={frame_count}): {stderr_encode}")

        cycle_duration = frame_count / float(safe_fps)
        repeats = max(1, math.ceil(target_duration / cycle_duration))
        concat_txt.write_text(
            "\n".join(f"file '{cycle_mp4}'" for _ in range(repeats)),
            encoding="utf-8",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        concat_cmd = [
            ffmpeg_exe,
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
        ]
        if abs((repeats * cycle_duration) - target_duration) > 0.05:
            concat_cmd.extend(["-t", str(target_duration)])
        concat_cmd.extend(["-c", "copy", "-movflags", "+faststart", str(output_path)])

        res_concat = subprocess.run(concat_cmd, capture_output=True, text=True)
        if res_concat.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(
                f"FFmpeg MP4 concat failed (rc={res_concat.returncode}): {res_concat.stderr}"
            )

    file_size = output_path.stat().st_size
    total_frames = int(round(target_duration * safe_fps))
    return {
        "codec": "h264",
        "container": "mp4",
        "pixel_format": "yuv420p",
        "duration_seconds": target_duration,
        "cycle_seconds": round(cycle_duration, 2),
        "cycle_frames": frame_count,
        "loop_repeats": repeats,
        "total_frames": total_frames,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "ffmpeg_binary": Path(ffmpeg_exe).name,
    }
