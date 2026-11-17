#!/usr/bin/env python3
"""High-speed Funny Donald Trump Video Corpus Generator for AI-Model.

Generates high-detail structured training datasets specializing in:
- Funny Donald Trump comedy, parody, and satirical meme video generation
- Iconic accordion hands gesture kinematics and signature oratory hand waves
- Signature golden-blonde swept bouffant hairstyle and hair-flutter motion
- Classic presidential dark navy tailored suit, crisp white collar, and iconic long red tie
- Warm sun-kissed golden apricot skin tones and Oval Office studio lighting
- Speech-synced comedic mouth articulation, humorous smirks, and animated head tilts
- Comedic rally dance sequences, podium press briefings, and viral meme reactions

Usage:
  python generate_trump_funny_video_corpus.py --size-mb 1.0
  python generate_trump_funny_video_corpus.py --samples 5000 --json-output trump_funny_video_corpus.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import time

TRUMP_SUBJECTS = [
    ("funny donald trump comedy caricature", "photorealistic satirical Donald Trump in presidential navy suit with signature red tie"),
    ("comedic donald trump rally speaker", "animated Donald Trump addressing roaring crowd with expressive hand gestures and warm smile"),
    ("donald trump viral dance meme avatar", "hilarious Donald Trump performing signature celebratory double thumbs-up podium dance"),
    ("funny donald trump press briefing host", "satirical Donald Trump at podium delivering humorous press conference with dramatic facial shrugs"),
    ("donald trump oval office parody presenter", "distinguished Donald Trump seated in Oval Office speaking directly to camera with comedic delivery"),
    ("cartoon donald trump animated caricature", "vibrant 2D cel-shaded Donald Trump comedy character with exaggerated facial expressions"),
    ("donail tum funy video meme parody", "humorous Donald Trump viral meme parody with playful comedic head tilts and signature blonde bouffant"),
    ("donald trump dramatic debate monologue", "theatrical Donald Trump delivering comedic debate rebuttal with signature accordion hand movements"),
    ("funny donald trump golf celebration", "casual Donald Trump on golf green making triumphant celebration gesture and laughing to camera"),
    ("presidential donald trump oratory host", "authentic photorealistic Donald Trump delivering high-energy comedic address with animated facial blendshapes"),
]

COMEDY_SCENARIOS = [
    ("delivering exaggerated speech with signature accordion hands motion", "rhythmic horizontal hand movements expanding and contracting in sync with comedic speech cadence"),
    ("performing viral celebratory rally dance at presidential podium", "playful double-fisted rhythmic sway with joyful comedic expressions and natural body weight shifts"),
    ("holding hilarious press conference with dramatic eyebrow raises", "satirical oratory delivery featuring signature lip pursing, humorous pauses, and direct camera eye contact"),
    ("delivering comedic Oval Office address with theatrical hand gestures", "authoritative yet playful demeanor with broad shoulder posture and smooth conversational pacing"),
    ("reacting to funny viral news meme with animated facial shrugs", "expressive ocular blinking, comedic cranial tilt, and warm golden studio key lighting"),
    ("giving humorous campaign rally monologue with crowd wave", "dynamic head turns, signature pointing gesture, and vibrant speech-synchronized mouth articulation"),
    ("celebrating golf tournament victory with triumphant thumbs-up", "high-energy celebratory demeanor with wind-blown hair physics and natural sunlight illumination"),
    ("delivering satirical boardroom comedy presentation", "confident executive posture with rhythmic finger taps, accordion hand gestures, and expressive brow motion"),
]

TRUMP_KINEMATICS = [
    ("signature accordion hand gesture harmonics", "iconic horizontal two-handed expansion delta_x(t) = 0.05 * sin(2.5 * phase) synchronized to oratorical emphasis"),
    ("cranial micro-sway and dramatic comedic head tilts", "expressive lateral head rotation theta_head(t) = 0.024 * sin(1.4 * phase) with natural comedic damping"),
    ("speech mouth articulation with signature lip pursing", "dynamic vertical jaw displacement delta_y = 0.022 * |sin(3.5 * phase)| with expressive smile transitions"),
    ("golden-blonde swept bouffant hair flutter physics", "subtle harmonic hair crest oscillation hair_sway(t) = 0.03 * cos(2.0 * phase) with zero jitter"),
    ("physiological respiration and broad shoulder posture", "rhythmic thoracic expansion w_breath(t) = 0.018 * sin(phase) maintaining broad executive silhouette"),
    ("expressive double thumbs-up and pointing gestures", "rhythmic forelimb articulation with natural comedic timing and smooth interpolation"),
]

WARDROBE_AND_AESTHETICS = [
    ("signature presidential navy suit with long red silk tie", "rich navy blue fabric RGB [0.10, 0.14, 0.24] with vibrant scarlet red tie RGB [0.88, 0.12, 0.16] and crisp white collar"),
    ("warm sun-kissed golden apricot skin tone", "bronzed photographic skin shading RGB [0.90, 0.70, 0.54] with natural subsurface scattering and key light highlights"),
    ("voluminous golden-blonde swept bouffant hairstyle", "signature sculpted blonde hair RGB [0.92, 0.80, 0.42] with dimensional studio rim light and subtle sheen"),
    ("warm Oval Office golden-hour studio lighting", "cinematic warm amber background bokeh with presidential drapery tones RGB [0.20, 0.16, 0.14]"),
    ("high-contrast satirical cartoon pop art grading", "saturated primary cel tones with crisp ink contours and bold comic-strip humor aesthetics"),
]

TIER_CONFIGS = [
    ("Flash tier", "320x240 @ 12 FPS", "low-latency 10-minute preview sequence"),
    ("Pro tier", "384x288 @ 12 FPS", "balanced high-detail 12-minute HD comedy sequence"),
    ("Advance tier", "480x360 @ 15 FPS", "high-fidelity 15-minute studio master comedy production"),
]

DURATIONS = [
    (600, "10 minute", "600s, 7,200 to 9,000 frames"),
    (720, "12 minute", "720s, 8,640 to 10,800 frames"),
    (900, "15 minute", "900s, 10,800 to 13,500 frames"),
    (1200, "20 minute", "1200s, 14,400 to 18,000 frames"),
]


def generate_trump_sample(idx: int) -> dict[str, str]:
    subj_label, subj_desc = random.choice(TRUMP_SUBJECTS)
    scen_label, scen_desc = random.choice(COMEDY_SCENARIOS)
    kin_label, kin_desc = random.choice(TRUMP_KINEMATICS)
    style_label, style_desc = random.choice(WARDROBE_AND_AESTHETICS)
    tier_name, res_label, tier_desc = random.choice(TIER_CONFIGS)
    dur_secs, dur_label, dur_desc = random.choice(DURATIONS)

    prompt_templates = [
        f"generate {dur_label} {subj_label} video {scen_label}",
        f"create {dur_label} funny donald trump comedy video {scen_label} in {tier_name}",
        f"render {dur_label} funny donail tum video {scen_label} with {kin_label}",
        f"animate funny donald trump meme video {scen_label} {res_label} mp4",
        f"synthesize {dur_label} humorous donald trump caricature video {scen_label} with {style_label}",
        f"produce funny donald trump comedy video {subj_label} {dur_label} {res_label}",
        f"generate funny donail tum funy video {scen_label} {dur_label} mp4",
    ]
    prompt = random.choice(prompt_templates)

    response = (
        f"Motion preset: Donald Trump comedic video synthesis featuring {subj_desc}. "
        f"Scenario: {scen_desc}. "
        f"Kinematics: {kin_desc}. "
        f"Wardrobe & Aesthetics: {style_desc}. "
        f"Encoding parameters: {res_label} at {dur_desc} ({dur_secs}s duration minimum), "
        f"synthesized seamlessly via {tier_name} NumPy keyframe harmonics and FFmpeg libx264 yuv420p."
    )

    return {
        "prompt": prompt,
        "response": response,
        "intent": "video_generation",
        "task": "video",
    }


def generate_trump_video_corpus(
    size_mb: float = 1.0,
    target_tokens: int | None = None,
    sample_count: int | None = None,
    json_path: Path | None = None,
    txt_path: Path | None = None,
) -> tuple[int, int]:
    """Generates structured Donald Trump funny video training pairs to JSON and TXT."""
    target_bytes = int(size_mb * 1024 * 1024) if size_mb and not target_tokens else None
    samples: list[dict[str, str]] = []

    txt_lines: list[str] = [
        "# AI-Model Platform - Funny Donald Trump Video Training Corpus",
        "# Modality: Video | Task: TaskType.VIDEO | Specialized: Donald Trump Comedy & Parody",
        "# Features: Accordion hands, golden bouffant hair, signature red tie, comedic rally dance",
        "",
    ]

    total_bytes = 0
    total_tokens = 0
    idx = 0

    while True:
        idx += 1
        s = generate_trump_sample(idx)
        samples.append(s)

        entry_text = (
            f"Prompt: {s['prompt']}\n"
            f"Response: {s['response']}\n"
            f"Task: video\n"
            f"Intent: video_generation\n\n"
        )
        txt_lines.append(entry_text)

        entry_bytes = len(entry_text.encode("utf-8"))
        entry_tokens = max(1, len(entry_text.split()))
        total_bytes += entry_bytes
        total_tokens += entry_tokens

        if sample_count and len(samples) >= sample_count:
            break
        if target_tokens and total_tokens >= target_tokens:
            break
        if target_bytes and total_bytes >= target_bytes:
            break

    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(samples, indent=2), encoding="utf-8")

    if txt_path:
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text("".join(txt_lines), encoding="utf-8")

    return len(samples), total_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Funny Donald Trump Video Training Corpus")
    parser.add_argument("--size-mb", type=float, default=1.0, help="Target file size in Megabytes (default: 1.0)")
    parser.add_argument("--tokens", type=int, default=None, help="Target token count")
    parser.add_argument("--samples", type=int, default=None, help="Exact sample count")
    parser.add_argument("--json-output", type=str, default=None, help="Output path for JSON dataset")
    parser.add_argument("--output", type=str, default=None, help="Output path for TXT corpus")

    args = parser.parse_args()

    default_dir = Path(__file__).resolve().parent
    json_out = Path(args.json_output) if args.json_output else default_dir / "trump_funny_video_corpus.json"
    txt_out = Path(args.output) if args.output else default_dir / "trump_funny_video_1m.txt"

    t0 = time.time()
    count, b_size = generate_trump_video_corpus(
        size_mb=args.size_mb,
        target_tokens=args.tokens,
        sample_count=args.samples or 1200,
        json_path=json_out,
        txt_path=txt_out,
    )
    elapsed = time.time() - t0

    print(f"Generated {count:,} Funny Donald Trump Video samples ({b_size / (1024*1024):.2f} MB) in {elapsed:.2f}s")
    print(f"  JSON dataset: {json_out}")
    print(f"  TXT corpus  : {txt_out}")


if __name__ == "__main__":
    main()

