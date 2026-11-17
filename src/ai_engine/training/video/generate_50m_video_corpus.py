#!/usr/bin/env python3
"""High-speed 50-Million Video Scale Corpus Generator for AI-Model.

Generates structured video synthesis training datasets covering motion fields,
camera dynamics, cartoon cel animation, plasma sweeps, particle orbits,
fluid mechanics, and temporal frame interpolation.

Usage:
  python generate_50m_video_corpus.py --tokens 50000000
  python generate_50m_video_corpus.py --samples 50000 --output video_motion_50m.txt
  python generate_50m_video_corpus.py --size-mb 50
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import random
import sys
import time

MOTION_MODES = [
    ("vortex", "cosmic vortex rotational swirl", "rotational phase theta(t) = omega * t + alpha * sin(2*pi*f*t)", "twilight"),
    ("ripple", "concentric radial ripple wave", "radial wave R(r, t) = J_0(k*r) * cos(omega*t - phi)", "viridis"),
    ("sweep", "directional laser matrix interference sweep", "directional sweep S(x, y, t) = sin(k_x*x - omega*t) * cos(k_y*y)", "plasma"),
    ("orbit", "orbital harmonic particle oscillation", "harmonic attractor pos(t) = [R*cos(omega*t), R*sin(omega*t), z_0*sin(2*omega*t)]", "inferno"),
    ("cartoon", "2D cel animation playful squash-and-stretch bounce", "elastic harmonic deformation y(t) = |sin(pi*f*t)| * exp(-gamma*t) with 5-level discrete cel quantization", "tab10"),
    ("solar", "solar flare coronal mass ejection turbulence", "turbulent magnetohydrodynamic field B(x,y,t) with Perlin fractal octaves", "magma"),
    ("aurora", "bioluminescent magnetic field curtain shimmer", "undulating curtain field A(x,y,t) = sum_i A_i * sin(k_i * x + v_i * t)", "turbo"),
    ("cyber", "cyberpunk neon grid raymarched horizon sweep", "perspective projective grid y_proj = H / (y + eps) with retro-wave bloom", "plasma"),
]

CAMERA_DYNAMICS = [
    "360-degree orbital flyaround with smooth quaternionic spherical interpolation (Slerp)",
    "slow dolly zoom (Hitchcock effect) with dynamic focal length compensation",
    "continuous axial roll with logarithmic forward z-axis drift",
    "smooth panoramic pan across 180-degree curved horizon with motion blur",
    "isometric axonometric tilt with rhythmic vertical pedestal oscillation",
    "FPV drone swoop diving through gravitational potential wells",
]

DURATIONS = [
    (600, "10 minute", "600s, 9,000 frames @ 15 FPS"),
    (720, "12 minute", "720s, 10,800 frames @ 15 FPS"),
    (900, "15 minute", "900s, 13,500 frames @ 15 FPS"),
    (1200, "20 minute", "1200s, 18,000 frames @ 15 FPS"),
    (1800, "30 minute", "1800s, 27,000 frames @ 15 FPS"),
]

COLORMAPS = [
    "plasma", "viridis", "inferno", "magma", "cividis", "twilight", "turbo", "tab10", "twilight_shifted"
]

FRAME_RESOLUTIONS = [
    ("320x240", "Flash tier 12 FPS"),
    ("384x288", "Pro tier 12 FPS"),
    ("480x360", "Advance tier 15 FPS"),
    ("640x480", "Studio HD tier 24 FPS"),
]


def generate_video_sample(idx: int) -> str:
    """Generate a high-detail video motion training sample."""
    mode, name, math_desc, def_lut = random.choice(MOTION_MODES)
    cam = random.choice(CAMERA_DYNAMICS)
    dur_sec, dur_label, frames_str = random.choice(DURATIONS)
    res, tier_desc = random.choice(FRAME_RESOLUTIONS)
    lut = random.choice(COLORMAPS) if random.random() < 0.4 else def_lut

    choice = random.random()
    if choice < 0.4:
        return (
            f"Question: How should the neural video pipeline synthesize a {dur_label} {mode} animation titled '{name}'?\n"
            f"Answer: Motion preset: {name}. Camera dynamics: {cam}. "
            f"Mathematical field formulation: {math_desc}. "
            f"Colormap LUT: {lut}. Target duration: {dur_label} ({frames_str}) at {res} ({tier_desc}). "
            f"Vectorized spatial tensors are computed across continuous phase intervals [0, 2*pi), "
            f"streamed directly into FFmpeg libx264 with YUV420p pixel format and +faststart atom optimization.\n"
        )
    elif choice < 0.7:
        return (
            f"Question: What temporal frame interpolation strategy optimizes 50-million frame scale rendering for {name}?\n"
            f"Answer: For {name}, temporal continuity is maintained using harmonic cyclic weights: "
            f"w_a(t) = (1 + cos(omega*t))/3, w_b(t) = (1 + cos(omega*t - 2pi/3))/3, w_c(t) = 1 - w_a - w_b. "
            f"This guarantees zero boundary jump cuts across multi-minute H.264 streams ({frames_str}). "
            f"Color grading utilizes the {lut} LUT with non-linear gamma curves for rich contrast.\n"
        )
    else:
        return (
            f"Question: Provide the generation prompt and specification for a {dur_label} {lut} {mode} video.\n"
            f"Answer: Prompt: 'animate {dur_label} {name} {lut} {res} h264 mp4'. "
            f"Specification: Synthesized {dur_label} ({frames_str}) H.264 MP4 {mode} video ({res}, {lut}). "
            f"Camera: {cam}. Core motion: {math_desc}.\n"
        )


def generate_video_corpus(
    output_path: Path,
    target_tokens: int | None = None,
    target_bytes: int | None = None,
    target_samples: int | None = None,
    chunk_size: int = 65536,
) -> tuple[int, int, float]:
    """Generate high-throughput video training dataset."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    tokens_estimated = 0
    sample_count = 0

    start_time = time.perf_counter()
    last_print = start_time

    chars_target = (target_tokens * 4) if target_tokens else (target_bytes or 50 * 1024 * 1024)
    if target_samples:
        chars_target = target_samples * 550

    print(f"[*] Generating Video Corpus to: {output_path}")
    if target_tokens:
        print(f"[*] Target Tokens: {target_tokens:,} (~{target_tokens / 1e6:.1f} Million tokens)")
    elif target_bytes:
        print(f"[*] Target Size: {target_bytes / (1024**2):.1f} MB")
    elif target_samples:
        print(f"[*] Target Samples: {target_samples:,}")

    buffer: list[str] = []
    buffer_bytes = 0

    with output_path.open("w", encoding="utf-8", buffering=1024 * 1024) as f:
        while True:
            sample = generate_video_sample(sample_count)
            sample_count += 1
            buffer.append(sample)
            buffer.append("\n")
            b_len = len(sample.encode("utf-8")) + 1
            buffer_bytes += b_len

            if buffer_bytes >= chunk_size:
                text = "".join(buffer)
                f.write(text)
                bytes_written += buffer_bytes
                tokens_estimated += len(text) // 4
                buffer = []
                buffer_bytes = 0

                now = time.perf_counter()
                if now - last_print >= 2.0:
                    elapsed = now - start_time
                    speed_mb = (bytes_written / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    tokens_per_sec = tokens_estimated / elapsed if elapsed > 0 else 0
                    pct = min(100.0, (bytes_written / chars_target) * 100.0)
                    print(
                        f"  -> Written: {bytes_written / (1024 * 1024):.1f} MB | "
                        f"Video Tokens: ~{tokens_estimated:,} | "
                        f"Samples: {sample_count:,} | "
                        f"Speed: {speed_mb:.1f} MB/s (~{tokens_per_sec:,.0f} tok/s) | "
                        f"Progress: {pct:.1f}%"
                    )
                    last_print = now

            if target_samples and sample_count >= target_samples:
                break
            if target_tokens and tokens_estimated >= target_tokens:
                break
            if target_bytes and bytes_written >= target_bytes:
                break
            if not target_tokens and not target_bytes and not target_samples and bytes_written >= chars_target:
                break

        if buffer:
            text = "".join(buffer)
            f.write(text)
            bytes_written += len(text.encode("utf-8"))
            tokens_estimated += len(text) // 4

    elapsed = max(0.001, time.perf_counter() - start_time)
    print(
        f"[✓] Video corpus generation complete in {elapsed:.2f}s! "
        f"Total: {bytes_written / (1024 * 1024):.2f} MB ({bytes_written / (1024**3):.3f} GB), "
        f"~{tokens_estimated:,} tokens, {sample_count:,} video motion samples. "
        f"Average Speed: {(bytes_written / (1024 * 1024)) / elapsed:.2f} MB/s"
    )
    return bytes_written, tokens_estimated, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 50-Million Video Scale Corpus")
    parser.add_argument("--tokens", type=str, default="50000000", help="Target token count (default: 50M)")
    parser.add_argument("--size-mb", type=float, default=0, help="Target file size in MB")
    parser.add_argument("--samples", type=int, default=0, help="Target sample count")
    parser.add_argument(
        "--output",
        type=str,
        default="src/ai_engine/training/video/video_motion_50m.txt",
        help="Target output file path",
    )

    args = parser.parse_args()

    target_tokens = None
    if args.tokens:
        tok_str = args.tokens.strip().upper()
        if tok_str.endswith("B"):
            target_tokens = int(float(tok_str[:-1]) * 1_000_000_000)
        elif tok_str.endswith("M"):
            target_tokens = int(float(tok_str[:-1]) * 1_000_000)
        elif tok_str.endswith("K"):
            target_tokens = int(float(tok_str[:-1]) * 1_000)
        else:
            target_tokens = int(tok_str.replace("_", "").replace(",", ""))

    target_bytes = int(args.size_mb * 1024 * 1024) if args.size_mb > 0 else None
    target_samples = args.samples if args.samples > 0 else None

    out_path = Path(args.output).resolve()
    generate_video_corpus(
        output_path=out_path,
        target_tokens=target_tokens,
        target_bytes=target_bytes,
        target_samples=target_samples,
    )


if __name__ == "__main__":
    main()

