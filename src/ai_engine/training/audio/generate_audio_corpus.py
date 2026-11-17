#!/usr/bin/env python3
"""High-speed Audio & Speech Scale Corpus Generator for AI-Model.

Generates structured audio synthesis and acoustic inspection training datasets covering:
- Edge-TTS neural speech synthesis and voice modulation
- OpenAI Whisper ASR speech recognition and timestamp extraction
- Librosa/Soundfile acoustic inspection (RMS energy, spectrograms, STFT, pitch)
- Multilingual voice synthesis (English, Bengali, Spanish, French, German)
- Multimodal audio-visual and biometric speech alignment

Usage:
  python generate_audio_corpus.py --samples 5000 --output audio_corpus.txt
  python generate_audio_corpus.py --size-mb 10 --output audio_corpus_10m.txt
  python generate_audio_corpus.py --json --samples 500 --output audio_generated.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time

VOICE_PROFILES = [
    ("en-US-JennyNeural", "American English female conversational assistant", "warm and empathetic", "24000 Hz"),
    ("en-US-GuyNeural", "American English male technical presenter", "confident and articulate", "24000 Hz"),
    ("en-GB-SoniaNeural", "British English female narrator", "authoritative and neutral", "24000 Hz"),
    ("en-GB-RyanNeural", "British English male executive narrator", "distinguished and professional", "24000 Hz"),
    ("bn-BD-NabanitaNeural", "Bengali (Bangladesh) female voice", "expressive and fluent", "24000 Hz"),
    ("bn-BD-PradeepNeural", "Bengali (Bangladesh) male commercial voice", "clear and resonant", "24000 Hz"),
    ("es-ES-ElviraNeural", "European Spanish female voice", "dynamic and natural", "24000 Hz"),
    ("fr-FR-DeniseNeural", "French female studio narrator", "melodic and refined", "24000 Hz"),
    ("de-DE-KatjaNeural", "German female voice assistant", "precise and modern", "24000 Hz"),
]

ASR_MODELS = [
    ("whisper-tiny", "39M parameters", "sub-100ms real-time audio transcription"),
    ("whisper-base", "74M parameters", "balanced speed and high word recognition accuracy"),
    ("whisper-small", "244M parameters", "multilingual transcription with low word error rate (WER)"),
    ("whisper-medium", "769M parameters", "studio-grade speech recognition with nuanced punctuation"),
]

ACOUSTIC_METRICS = [
    ("Root Mean Square (RMS) energy", "librosa.feature.rms(y=y, frame_length=2048, hop_length=512)", "decibels relative to full scale (dBFS)"),
    ("Short-Time Fourier Transform (STFT)", "librosa.stft(y, n_fft=2048, hop_length=512, window='hann')", "time-frequency complex matrix"),
    ("Spectral Centroid", "librosa.feature.spectral_centroid(y=y, sr=sr)", "center of mass of the frequency spectrum"),
    ("Zero-Crossing Rate (ZCR)", "librosa.feature.zero_crossing_rate(y=y)", "rate of sign-changes along the audio waveform"),
    ("Mel-Frequency Cepstral Coefficients (MFCC)", "librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)", "compact timbre representation for speech recognition"),
]

AUDIO_USE_CASES = [
    ("FinTech payment voice alert", "confirming bKash, Nagad, or credit card wallet transaction settlements"),
    ("interactive AI customer support agent", "real-time two-way voice dialogue with low latency"),
    ("podcast audio intro and outro", "synthesizing branded opening voiceover with background audio bed"),
    ("multilingual audio translation", "transcribing source speech via Whisper and synthesizing target speech via Edge-TTS"),
    ("meeting minutes speech-to-text", "generating speaker-segmented transcripts with precise start and end timestamps"),
]


def generate_audio_sample(idx: int) -> dict[str, str]:
    """Generate a structured audio training sample."""
    choice = random.random()
    if choice < 0.45:
        voice, desc, tone, sr = random.choice(VOICE_PROFILES)
        use_case, uc_desc = random.choice(AUDIO_USE_CASES)
        prompt = f"synthesize {desc} for {use_case} using edge tts {voice}"
        response = (
            f"Configure AudioPipeline with voice='{voice}', sample_rate={sr}. "
            f"Use case: {use_case} ({uc_desc}). Tone profile: {tone}. "
            f"The Edge-TTS engine streams audio chunks asynchronously, encodes output to high-fidelity MP3/WAV, "
            f"and provides instant HTML5 playback in the frontend studio."
        )
        intent = "audio_generation"
    elif choice < 0.75:
        model, params, capability = random.choice(ASR_MODELS)
        use_case, uc_desc = random.choice(AUDIO_USE_CASES)
        prompt = f"transcribe audio file for {use_case} using {model} speech to text"
        response = (
            f"Execute Whisper ASR transcription pipeline using model '{model}' ({params}). "
            f"Input is resampled to 16,000 Hz single-channel PCM float32. "
            f"The model provides {capability}, returning text transcription, language detection, "
            f"and word-level timestamps suitable for {uc_desc}."
        )
        intent = "audio_transcription"
    else:
        metric, formula, meaning = random.choice(ACOUSTIC_METRICS)
        prompt = f"compute acoustic {metric} from audio waveform using librosa"
        response = (
            f"Call AudioPipeline.analyze_audio() or execute: `{formula}`. "
            f"This extracts {metric}, quantifying {meaning}. "
            f"The resulting feature array enables noise floor evaluation, speech brightness grading, "
            f"and acoustic anomaly detection in the audio signal."
        )
        intent = "audio_analysis"

    return {
        "prompt": prompt,
        "response": response,
        "intent": intent,
        "task": "audio",
    }


def generate_qa_text(sample: dict[str, str]) -> str:
    """Format dict sample into structured Question / Answer text block."""
    return f"Question: {sample['prompt']}\nAnswer: {sample['response']}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate scalable audio training datasets.")
    parser.add_argument("--samples", type=int, default=1000, help="Number of training samples to generate.")
    parser.add_argument("--size-mb", type=float, default=None, help="Target file size in megabytes.")
    parser.add_argument("--output", type=str, default="audio_corpus_sample.txt", help="Output file path.")
    parser.add_argument("--json", action="store_true", help="Output as JSON array instead of Q&A text.")
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Generating audio corpus to: {out_path}")
    start_time = time.perf_counter()

    if args.json:
        data = [generate_audio_sample(i) for i in range(args.samples)]
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        elapsed = time.perf_counter() - start_time
        print(f"[+] Wrote {len(data)} JSON samples ({out_path.stat().st_size:,} bytes) in {elapsed:.2f}s")
    else:
        target_bytes = int(args.size_mb * 1024 * 1024) if args.size_mb else None
        bytes_written = 0
        count = 0

        with out_path.open("w", encoding="utf-8", buffering=64 * 1024) as f:
            while True:
                sample = generate_audio_sample(count)
                text = generate_qa_text(sample) + "\n"
                f.write(text)
                bytes_written += len(text.encode("utf-8"))
                count += 1

                if target_bytes and bytes_written >= target_bytes:
                    break
                if not target_bytes and count >= args.samples:
                    break

        elapsed = time.perf_counter() - start_time
        print(f"[+] Wrote {count:,} Q&A samples ({bytes_written:,} bytes) in {elapsed:.2f}s")


if __name__ == "__main__":
    main()

