"""Curated multi-intent instruction dataset for tblinc neural training."""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import TaskType, TrainingSample

TRAINING_ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_PATH = TRAINING_ROOT_DIR / "training_corpus.json"
EXTRA_CORPORA_DIR = TRAINING_ROOT_DIR / "corpora"
MODALITY_CORPORA_DIRS: tuple[Path, ...] = (
    TRAINING_ROOT_DIR / "chat",
    TRAINING_ROOT_DIR / "code",
    TRAINING_ROOT_DIR / "images",
    TRAINING_ROOT_DIR / "video",
    TRAINING_ROOT_DIR / "audio",
    EXTRA_CORPORA_DIR,
)

INTENT_LABELS: tuple[str, ...] = (
    "greeting",
    "math_compute",
    "code_python",
    "code_typescript",
    "code_sql",
    "code_bash",
    "debugging",
    "architecture",
    "image_generation",
    "video_generation",
    "audio_generation",
    "audio_transcription",
    "audio_analysis",
    "rag_knowledge",
    "conversation_memory",
    "billing_quota",
    "training_ml",
    "comparison",
    "explanation",
    "text_corpus",
    "general",
)

_CORE_TRAINING_SAMPLES: tuple[TrainingSample, ...] = (
    TrainingSample(
        prompt="hello hi hey good morning welcome",
        response="Hello! I am tblinc v1, ready to assist with engineering, math, code generation, images, and video.",
        intent="greeting",
    ),
    TrainingSample(
        prompt="how are you how is it going good afternoon thanks thank you",
        response="Doing great, thanks for asking! I am tblinc v1 — how can I help you today?",
        intent="greeting",
    ),
    TrainingSample(
        prompt="who are you what can you do help capabilities",
        response="tblinc v1 supports multi-turn contextual chat, Python/TypeScript/SQL/Bash code synthesis, and image/video rendering.",
        intent="greeting",
    ),
    TrainingSample(
        prompt="calculate 24 * 7 + 12 math equation compute sum product",
        response="Exact mathematical expressions are parsed and evaluated safely via AST arithmetic operations.",
        intent="math_compute",
    ),
    TrainingSample(
        prompt="solve sqrt(144) plus percentage 15% of 240 divide multiply",
        response="Mathematical queries compute exact numeric outputs, operator precedence, and unit breakdowns.",
        intent="math_compute",
    ),
    TrainingSample(
        prompt="write python fastapi endpoint async httpx client pytest",
        response="Use modular FastAPI routers with Pydantic schemas, dependency injection, and async httpx clients.",
        intent="code_python",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="create django model view serializer rest framework python function",
        response="Define normalized Django models with explicit foreign keys, DRF serializers, and IsAuthenticated permission classes.",
        intent="code_python",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="write typescript react component interface axios api client tsx",
        response="Use strongly typed TypeScript interfaces, clean hooks, and Axios interceptors for authenticated API calls.",
        intent="code_typescript",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="build vue frontend store dark theme tailwindcss typescript",
        response="Centralize reactive state, sync the root dark class, and keep components decoupled from HTTP transport.",
        intent="code_typescript",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="write sql postgres select join group by table migration index",
        response="Write parameterized SQL queries with selective indexes and transactional integrity.",
        intent="code_sql",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="query postgres database usage transactions credits sum",
        response="Aggregate quota logs and transaction records by user_id and model_tier using SQL GROUP BY.",
        intent="code_sql",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="bash shell script curl command systemctl docker makefile",
        response="Use strict shell scripts (`set -euo pipefail`) with explicit exit checks and curl timeouts.",
        intent="code_bash",
        task=TaskType.CODE,
    ),
    TrainingSample(
        prompt="debug fix error exception traceback 401 404 500 cors disallowedhost",
        response="Inspect authentication headers, ALLOWED_HOSTS, CORS origin settings, and backend service logs first.",
        intent="debugging",
    ),
    TrainingSample(
        prompt="troubleshoot broken api postgresql socket connection refused migration failed",
        response="Verify service health endpoints, inspect PostgreSQL socket connectivity, and confirm Django migrations match models.",
        intent="debugging",
    ),
    TrainingSample(
        prompt="design scalable architecture microservices queue system cache backend",
        response="Decouple stateless compute workers from transactional state, enforce schema contracts, and monitor p95 latency.",
        intent="architecture",
    ),
    TrainingSample(
        prompt="how to structure authentication gateway billing quota pipeline",
        response="Separate JWT identity verification (Djoser) and credit accounting (Django) from neural compute pipelines (FastAPI + ai_engine).",
        intent="architecture",
    ),
    TrainingSample(
        prompt="draw render generate image illustration portrait logo artwork",
        response="Route visual prompts through the spatial synthesis image pipeline with tier-scaled resolution.",
        intent="image_generation",
        task=TaskType.IMAGES,
    ),
    TrainingSample(
        prompt="create video animation motion frames clip render gif",
        response="Synthesize interpolated keyframe tensors into multi-frame animated GIF sequences via VideoPipeline.",
        intent="video_generation",
        task=TaskType.VIDEO,
    ),
    TrainingSample(
        prompt="synthesize speech voice audio narration text to speech edge tts sound",
        response="Synthesize lifelike human speech and narration using Edge-TTS with natural neural voices and pitch modulation.",
        intent="audio_generation",
        task=TaskType.AUDIO,
    ),
    TrainingSample(
        prompt="transcribe audio file speech to text whisper asr recording timestamps",
        response="Transcribe recorded speech to text using OpenAI Whisper with language detection and word-level timestamps.",
        intent="audio_transcription",
        task=TaskType.AUDIO,
    ),
    TrainingSample(
        prompt="analyze audio acoustic inspection waveform spectrogram sample rate librosa soundfile",
        response="Inspect acoustic properties: duration, sample rate, RMS energy, spectral centroid, and STFT spectrograms via Librosa.",
        intent="audio_analysis",
        task=TaskType.AUDIO,
    ),
    TrainingSample(
        prompt="search retrieve knowledge base documents vector memory rag chroma embeddings",
        response="Query ChromaDB vector memory with dense sentence-transformers embeddings for sub-linear semantic context retrieval.",
        intent="rag_knowledge",
        task=TaskType.CHAT,
    ),
    TrainingSample(
        prompt="what did i say earlier summarize conversation remember my name previous turn",
        response="Conversation history is loaded directly from persisted messages and injected into multi-turn reasoning.",
        intent="conversation_memory",
    ),
    TrainingSample(
        prompt="follow up continue previous answer explain earlier point more simply",
        response="Follow-up prompts reference earlier conversation turns for continuity and refinement.",
        intent="conversation_memory",
    ),
    TrainingSample(
        prompt="billing subscription credits quota pricing plans flash pro advance",
        response="Starter grants 250 credits; Flash costs 1-8 cr, Pro costs 3-20 cr, and Advance costs 6-36 cr depending on modality.",
        intent="billing_quota",
    ),
    TrainingSample(
        prompt="train model neural network fine tune epochs loss accuracy weights checkpoint numpy",
        response="Neural training runs backpropagation across NumPy, PyTorch, TensorFlow, and Keras backends and saves checkpoints to disk.",
        intent="training_ml",
    ),
    TrainingSample(
        prompt="compare vs difference between numpy pytorch tensorflow keras flash pro",
        response="Compare NumPy vectorized CPU speed against PyTorch, TensorFlow, and Keras by latency, hardware placement, and efficiency.",
        intent="comparison",
    ),
    TrainingSample(
        prompt="explain how transformer attention neural encoding works concept",
        response="Tokens map to dense embeddings, contextualize via multi-layer encoders, and pool into normalized latent vectors.",
        intent="explanation",
    ),
    TrainingSample(
        prompt="plan summarize checklist advice brainstorm outline guide",
        response="Structure complex goals into clear stages, concrete deliverables, and measurable verification checks.",
        intent="general",
    ),
)


def load_json_dataset(json_path: Path) -> list[TrainingSample]:
    """Load TrainingSample entries from a .json or .jsonl file without artificial size caps."""
    if not json_path.exists():
        return []
    raw_text = json_path.read_text(encoding="utf-8-sig").strip()
    if not raw_text:
        return []

    records: list[object]
    if json_path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
    else:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            nested = parsed.get("samples") or parsed.get("data") or []
            records = list(nested) if isinstance(nested, list) else []
        elif isinstance(parsed, list):
            records = parsed
        else:
            records = []

    loaded: list[TrainingSample] = []
    for item in records:
        if isinstance(item, dict):
            loaded.append(TrainingSample.model_validate(item))
    return loaded


def iter_txt_dataset(
    txt_path: Path,
    intent: str = "text_corpus",
    task: TaskType = TaskType.CHAT,
):
    """Yield TrainingSample items lazily from raw .txt files without high memory usage."""
    if not txt_path.exists():
        return

    current_q = ""
    current_a: list[str] = []
    buffer: list[str] = []

    with txt_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                if current_q and current_a:
                    yield TrainingSample(
                        prompt=current_q[:500],
                        response="\n".join(current_a)[:4000],
                        intent=intent,
                        task=task,
                    )
                    current_q = ""
                    current_a = []
                elif buffer:
                    para = " ".join(buffer).strip()
                    buffer = []
                    if len(para) >= 15:
                        for delim in ("?", "\n", ".", ":"):
                            if delim in para:
                                parts = para.split(delim, 1)
                                p_cand = parts[0].strip() + (delim if delim in ("?", ".") else "")
                                r_cand = parts[1].strip()
                                if len(p_cand) >= 5 and len(r_cand) >= 10:
                                    yield TrainingSample(
                                        prompt=p_cand[:500],
                                        response=r_cand[:4000],
                                        intent=intent,
                                        task=task,
                                    )
                                    break
                        else:
                            words = para.split()
                            p_cand = " ".join(words[:min(10, len(words))])
                            yield TrainingSample(
                                prompt=p_cand[:500],
                                response=para[:4000],
                                intent=intent,
                                task=task,
                            )
                continue

            lowered = stripped.lower()
            if lowered.startswith(("q:", "question:", "user:", "prompt:")):
                if current_q and current_a:
                    yield TrainingSample(
                        prompt=current_q[:500],
                        response="\n".join(current_a)[:4000],
                        intent=intent,
                        task=task,
                    )
                current_q = stripped.split(":", 1)[1].strip()
                current_a = []
            elif lowered.startswith(("a:", "answer:", "assistant:", "response:")):
                current_a = [stripped.split(":", 1)[1].strip()]
            elif current_q:
                current_a.append(stripped)
            else:
                buffer.append(stripped)

        if current_q and current_a:
            yield TrainingSample(
                prompt=current_q[:500],
                response="\n".join(current_a)[:4000],
                intent=intent,
                task=task,
            )
        elif buffer:
            para = " ".join(buffer).strip()
            if len(para) >= 15:
                words = para.split()
                yield TrainingSample(
                    prompt=" ".join(words[:min(10, len(words))])[:500],
                    response=para[:4000],
                    intent=intent,
                    task=task,
                )


def load_txt_dataset(
    txt_path: Path,
    max_samples: int = 50000,
    intent: str = "text_corpus",
    task: TaskType = TaskType.CHAT,
) -> list[TrainingSample]:
    """Stream and parse raw .txt file (even 1GB+) into structured TrainingSamples.
    
    Supports:
    - Structured Q&A pairs (Q: ... A: ... or User: ... Assistant: ...)
    - Paragraph blocks separated by blank lines
    - Sentence/passage sliding windows for continuous prose
    """
    import itertools
    return list(itertools.islice(iter_txt_dataset(txt_path, intent=intent, task=task), max_samples))


def _iter_corpus_files() -> list[Path]:
    """Return sorted JSON/JSONL/TXT corpus files across modality directories and extra corpora."""
    files: list[Path] = []
    for directory in MODALITY_CORPORA_DIRS:
        if not directory.is_dir():
            continue
        for entry in sorted(directory.rglob("*")):
            if entry.is_file() and entry.suffix.lower() in {".json", ".jsonl", ".txt"}:
                files.append(entry)
    return files


def load_builtin_corpus(corpus_path: Path | None = None) -> tuple[TrainingSample, ...]:
    """Merge core anchors, main JSON corpus, and modality/*.json/*.txt corpora cleanly."""
    target_path = corpus_path or DEFAULT_CORPUS_PATH
    sources: list[TrainingSample] = [*_CORE_TRAINING_SAMPLES]
    if target_path.exists():
        if target_path.suffix.lower() == ".txt":
            sources.extend(load_txt_dataset(target_path))
        else:
            sources.extend(load_json_dataset(target_path))

    if corpus_path is None:
        for extra_file in _iter_corpus_files():
            if extra_file.suffix.lower() == ".txt":
                parent_name = extra_file.parent.name.lower()
                modality_task = (
                    TaskType.AUDIO
                    if parent_name == "audio"
                    else (
                        TaskType.VIDEO
                        if parent_name == "video"
                        else (
                            TaskType.CODE
                            if parent_name == "code"
                            else (TaskType.IMAGES if parent_name == "images" else TaskType.CHAT)
                        )
                    )
                )
                modality_intent = f"{modality_task.value}_generation" if modality_task != TaskType.CHAT else "text_corpus"
                sources.extend(load_txt_dataset(extra_file, max_samples=500, intent=modality_intent, task=modality_task))
            else:
                sources.extend(load_json_dataset(extra_file))

    merged_by_key: dict[str, TrainingSample] = {}
    for sample in sources:
        key = f"{sample.task.value}::{sample.prompt.strip().lower()}"
        existing = merged_by_key.get(key)
        if existing is None or ("\n" in sample.response and "\n" not in existing.response):
            merged_by_key[key] = sample
    return tuple(merged_by_key.values())


BUILTIN_TRAINING_SAMPLES: tuple[TrainingSample, ...] = load_builtin_corpus()


def dataset_summary() -> dict[str, object]:
    """Return high-level metrics describing the active built-in + modality JSON corpora."""
    corpus_files = ([DEFAULT_CORPUS_PATH] if DEFAULT_CORPUS_PATH.exists() else []) + _iter_corpus_files()
    corpus_bytes = sum(path.stat().st_size for path in corpus_files if path.exists())
    code_samples = [s for s in BUILTIN_TRAINING_SAMPLES if s.task == TaskType.CODE]
    audio_samples = [s for s in BUILTIN_TRAINING_SAMPLES if s.task == TaskType.AUDIO]
    task_counts: dict[str, int] = {
        TaskType.CHAT.value: 0,
        TaskType.CODE.value: 0,
        TaskType.IMAGES.value: 0,
        TaskType.VIDEO.value: 0,
        TaskType.AUDIO.value: 0,
    }
    for s in BUILTIN_TRAINING_SAMPLES:
        task_counts[s.task.value] = task_counts.get(s.task.value, 0) + 1
    return {
        "sample_count": len(BUILTIN_TRAINING_SAMPLES),
        "intent_count": len({s.intent for s in BUILTIN_TRAINING_SAMPLES}),
        "task_counts": task_counts,
        "code_sample_count": len(code_samples),
        "audio_sample_count": len(audio_samples),
        "runnable_code_count": sum(1 for s in code_samples if "\n" in s.response),
        "corpus_files": [str(path.relative_to(TRAINING_ROOT_DIR)) for path in corpus_files],
        "corpus_path": str(DEFAULT_CORPUS_PATH),
        "corpus_bytes": corpus_bytes,
    }

