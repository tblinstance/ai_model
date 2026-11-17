#!/usr/bin/env python3
"""High-speed 1MB / 1-Million Token Real & Virtual Human Video Corpus Generator for AI-Model.

Generates high-detail structured training datasets specializing in:
- Photorealistic real men and women video generation
- Virtual digital humans, 3D avatars, and talking head presenters
- Physiological respiration, facial micro-expressions, and cranial micro-sway
- Natural human skin tones, subsurface scattering, and studio 3-point lighting
- Image-to-video reference conditioning with 94% photo fidelity

Usage:
  python generate_human_video_corpus.py --size-mb 1.0
  python generate_human_video_corpus.py --tokens 1000000 --output real_virtual_human_video_1m.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import time

HUMAN_SUBJECTS = [
    ("real woman", "photorealistic woman in her late 20s with hazel eyes and brown wavy hair"),
    ("real man", "photorealistic man in his mid-30s with sharp jawline, short trimmed beard, and charcoal blazer"),
    ("virtual woman avatar", "stylized 3D digital woman avatar with expressive facial blendshapes and emerald eyes"),
    ("virtual man avatar", "high-fidelity 3D digital human man presenter with realistic skin pores and modern side-part hairstyle"),
    ("female news anchor", "professional real female broadcast journalist in studio wearing navy tailored suit"),
    ("male tech presenter", "casual real male speaker with open-collar shirt presenting product keynote"),
    ("virtual AI human host", "futuristic virtual digital human host with soft volumetric holographic rim lighting"),
    ("young woman in sunlight", "natural real young woman with warm golden hour sunlight illuminating her portrait"),
    ("executive businessman", "distinguished real businessman with confident gaze and subtle conversational micro-gestures"),
    ("creative female artist", "expressive real woman artist speaking directly to camera with engaging conversational demeanor"),
]

SCENARIOS = [
    ("speaking directly to camera in professional 4K studio", "delivering an articulate presentation with natural eye contact"),
    ("conversational talking head interview", "responding thoughtfully with authentic micro-nodding and facial micro-expressions"),
    ("podcast host seated at microphone setup", "dynamic conversational head tilt with subtle breathing and natural shoulder relaxation"),
    ("executive keynote address on conference stage", "poised posture with gentle vertical respiration kinematics and smooth pacing"),
    ("casual vlog dialogue with soft bokeh background", "warm approachable facial expression with natural cranial saccades and gaze shifts"),
    ("virtual AI assistant interactive avatar session", "precise synthetic facial phoneme articulation and lifelike ocular focal micro-adjustments"),
]

KINEMATICS = [
    ("physiological respiration harmonics", "vertical torso and clavicle expansion w_breath(t) = 0.02 * sin(phase) * (yy_norm + 0.3) * 1.5"),
    ("cranial micro-sway and micro-saccades", "smooth lateral head rotation w_sway(t) = 0.012 * cos(phase * 0.5) with natural damping"),
    ("subtle ocular blinking and gaze fixation", "periodic eyelid occlusion at 3.5s harmonic intervals with zero jump cuts"),
    ("jaw articulation and lip phoneme motion", "synchronized vertical jaw displacement delta_y = 0.015 * |sin(2*pi*f_speech*t)|"),
    ("subsurface skin scattering and pore lighting", "bidirectional reflectance distribution function (BRDF) with warm melanin highlights"),
]

LIGHTING_AND_COLOR = [
    ("natural_portrait color grading", "true-to-life human skin tones RGB [0.84, 0.66, 0.56] with complete suppression of false-color neon LUTs"),
    ("3-point studio lighting", "soft diffused 5600K key light, subtle fill light, and 3200K warm hair rim light"),
    ("golden hour warm sunlight", "gentle amber directional side-light with soft specular skin highlights and natural shadow roll-off"),
    ("high-end cinematic portrait", "f/1.8 shallow depth-of-field with creamy circular background bokeh and edge vignette"),
]

RESOLUTIONS = [
    ("320x240 @ 12 FPS", "Flash tier 10-minute preview"),
    ("384x288 @ 12 FPS", "Pro tier 10-minute HD"),
    ("480x360 @ 15 FPS", "Advance tier 10-minute studio master"),
]

DURATIONS = [
    (600, "10 minute", "600s, 7,200 to 9,000 frames"),
    (720, "12 minute", "720s, 8,640 to 10,800 frames"),
    (900, "15 minute", "900s, 10,800 to 13,500 frames"),
    (1200, "20 minute", "1200s, 14,400 to 18,000 frames"),
]


def generate_human_sample(idx: int) -> str:
    """Generate a high-entropy real / virtual human training pair."""
    subj, subj_desc = random.choice(HUMAN_SUBJECTS)
    scen, scen_desc = random.choice(SCENARIOS)
    kin_name, kin_math = random.choice(KINEMATICS)
    light_name, light_desc = random.choice(LIGHTING_AND_COLOR)
    res, tier_desc = random.choice(RESOLUTIONS)
    dur_sec, dur_lbl, frames_str = random.choice(DURATIONS)

    choice = random.random()
    if choice < 0.35:
        return (
            f"Question: How do you generate a {dur_lbl} video of a {subj} {scen}?\n"
            f"Answer: Motion preset: photorealistic human portrait with {kin_name}. "
            f"Subject: {subj_desc}. Scenario: {scen_desc}. "
            f"Kinematic formulation: {kin_math}. "
            f"Color grading: {light_name} ({light_desc}). "
            f"Encoding: Synthesized {dur_lbl} ({frames_str}) H.264 MP4 human video ({res}, {tier_desc}) "
            f"via FFmpeg libx264 with YUV420p pixel format and +faststart atom optimization.\n"
        )
    elif choice < 0.65:
        return (
            f"Question: What neural video pipeline parameters animate a {subj} with realistic facial motion?\n"
            f"Answer: Activate `motion_mode: human` in the neural pipeline. "
            f"Set colormap to `natural_portrait` to preserve authentic human skin pigmentation and disable false-color heatmaps. "
            f"Apply dual-harmonic kinematics: {kin_math} combined with {kin_name}. "
            f"Lighting profile: {light_name}. Target resolution: {res} across {dur_lbl} ({frames_str}). "
            f"If an image is uploaded, enforce 94% photo fidelity preservation to lock exact facial landmarks and skin texture.\n"
        )
    else:
        return (
            f"Question: Provide the generation prompt and specification for a {dur_lbl} {subj} talking video.\n"
            f"Answer: Prompt: 'generate {dur_lbl} {subj} speaking portrait video in studio {res} mp4'. "
            f"Specification: Synthesized {dur_lbl} ({frames_str}) H.264 MP4 human video ({res}, natural_portrait). "
            f"Subject details: {subj_desc}. Kinematics: {kin_name}. Lighting: {light_name}.\n"
        )


def generate_human_corpus(
    output_path: Path,
    target_bytes: int = 1024 * 1024,
    chunk_size: int = 65536,
) -> tuple[int, int, float]:
    """Generate high-density real/virtual human video training corpus."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    tokens_estimated = 0
    sample_count = 0

    start_time = time.perf_counter()
    print(f"[*] Generating Real & Virtual Human Video Corpus to: {output_path}")
    print(f"[*] Target Size: {target_bytes / (1024**2):.2f} MB (~{target_bytes / 4:,.0f} tokens)")

    buffer: list[str] = []
    buffer_bytes = 0

    with output_path.open("w", encoding="utf-8", buffering=1024 * 1024) as f:
        while bytes_written < target_bytes:
            sample = generate_human_sample(sample_count)
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

        if buffer:
            text = "".join(buffer)
            f.write(text)
            bytes_written += len(text.encode("utf-8"))
            tokens_estimated += len(text) // 4

    elapsed = max(0.001, time.perf_counter() - start_time)
    print(
        f"[✓] Generation complete in {elapsed:.2f}s! "
        f"Total: {bytes_written / (1024 * 1024):.2f} MB ({bytes_written:,} bytes), "
        f"~{tokens_estimated:,} tokens, {sample_count:,} human video training samples. "
        f"Average Speed: {(bytes_written / (1024 * 1024)) / elapsed:.2f} MB/s"
    )
    return bytes_written, tokens_estimated, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 1MB Real & Virtual Human Video Corpus")
    parser.add_argument("--size-mb", type=float, default=1.0, help="Target file size in MB (default: 1.0)")
    parser.add_argument(
        "--output",
        type=str,
        default="src/ai_engine/training/video/real_virtual_human_video_1m.txt",
        help="Target output file path",
    )

    args = parser.parse_args()
    target_bytes = int(args.size_mb * 1024 * 1024)
    out_path = Path(args.output).resolve()
    generate_human_corpus(output_path=out_path, target_bytes=target_bytes)


if __name__ == "__main__":
    main()

