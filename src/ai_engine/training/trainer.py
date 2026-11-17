"""Neural trainer, checkpoint persistence, and knowledge retrieval memory."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from uuid import uuid4

from ..backends import BaseNeuralBackend
from ..config import TIER_SPECS
from ..models import BaseAIModel
from ..schemas import (
    AllTiersTrainingResult,
    BackendTrainingStats,
    CheckpointInfo,
    EvaluationRequest,
    EvaluationResult,
    FrameworkBackend,
    ModelTier,
    TaskType,
    TrainingRequest,
    TrainingResult,
    TrainingSample,
    TrainingStatusResponse,
)
from ..utils import LatencyTimer, NeuralTokenizer
from .dataset import BUILTIN_TRAINING_SAMPLES, INTENT_LABELS, load_json_dataset


_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do",
        "for", "from", "how", "i", "in", "into", "is", "it", "of", "on",
        "or", "should", "the", "to", "vs", "what", "when", "where", "which",
        "who", "why", "with",
    }
)


class NeuralTrainer:
    """Coordinates gradient-based training across NumPy, PyTorch, TensorFlow, and Keras."""

    STATE_FILENAME = "training_state.json"
    KNOWLEDGE_FILENAME = "knowledge_base.json"

    def __init__(self, checkpoint_dir: Path, tokenizer: NeuralTokenizer) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.tokenizer = tokenizer
        self.intent_labels: list[str] = list(INTENT_LABELS)
        self.custom_samples: list[TrainingSample] = []
        self.knowledge_samples: list[TrainingSample] = []
        self._indexed_entries: list[tuple[TrainingSample, frozenset[str], str, bool]] = []
        self._token_index: dict[str, list[int]] = {}
        self.last_training: TrainingResult | None = None
        self._rebuild_knowledge_index(include_builtin=True)

    def _intent_id(self, intent: str) -> int:
        normalized = intent.strip().lower().replace(" ", "_") or "general"
        if normalized in self.intent_labels:
            return self.intent_labels.index(normalized)
        return self.intent_labels.index("general")

    def _checkpoint_file(self, backend_name: str, tier: ModelTier) -> Path:
        ext = "pt" if backend_name == "pytorch" else "npz"
        return self.checkpoint_dir / f"{backend_name}_{tier.value}.{ext}"

    def load_saved_state(
        self,
        backends: dict[str, BaseNeuralBackend],
        models: dict[ModelTier, BaseAIModel],
    ) -> None:
        """Load persisted checkpoints, custom knowledge, and training status if present."""
        state_file = self.checkpoint_dir / self.STATE_FILENAME
        kb_file = self.checkpoint_dir / self.KNOWLEDGE_FILENAME

        if kb_file.exists():
            try:
                raw_samples = json.loads(kb_file.read_text(encoding="utf-8"))
                self.custom_samples = [TrainingSample.model_validate(item) for item in raw_samples]
                self._rebuild_knowledge_index(include_builtin=True)
            except Exception:
                self.custom_samples = []

        if state_file.exists():
            try:
                self.last_training = TrainingResult.model_validate_json(state_file.read_text(encoding="utf-8"))
            except Exception:
                self.last_training = None

        for tier, spec in TIER_SPECS.items():
            for backend_name, backend in backends.items():
                if not backend.health().available:
                    continue
                ckpt = self._checkpoint_file(backend_name, tier)
                if ckpt.exists():
                    try:
                        backend.load_weights(
                            checkpoint_path=ckpt,
                            hidden_dim=spec.hidden_dim,
                            num_layers=spec.num_layers,
                            vocab_size=spec.vocab_size,
                        )
                    except Exception:
                        continue
        _ = models

    def _rebuild_knowledge_index(self, include_builtin: bool = True) -> None:
        seen: set[str] = set()
        merged: list[TrainingSample] = []
        custom_keys = {f"{s.task.value}::{s.prompt.strip().lower()}" for s in self.custom_samples}
        source_lists = [self.custom_samples, list(BUILTIN_TRAINING_SAMPLES) if include_builtin else []]
        for group in source_lists:
            for sample in group:
                key = f"{sample.task.value}::{sample.prompt.strip().lower()}"
                if key not in seen:
                    seen.add(key)
                    merged.append(sample)
        self.knowledge_samples = merged

        indexed: list[tuple[TrainingSample, frozenset[str], str, bool]] = []
        token_index: dict[str, list[int]] = {}
        for idx, sample in enumerate(merged):
            lowered_prompt = sample.prompt.strip().lower()
            cand_tokens = frozenset(
                tok.lower()
                for tok in self.tokenizer.tokenize(sample.prompt)
                if len(tok) > 1 or tok.isalnum()
            )
            index_tokens = [tok for tok in cand_tokens if tok not in _STOPWORDS] or list(cand_tokens)
            is_custom = f"{sample.task.value}::{lowered_prompt}" in custom_keys
            indexed.append((sample, cand_tokens, lowered_prompt, is_custom))
            for tok in index_tokens:
                token_index.setdefault(tok, []).append(idx)
        self._indexed_entries = indexed
        self._token_index = token_index

    def import_json_corpus(self, json_path: Path, merge: bool = True) -> int:
        """Load samples from an arbitrary JSON/JSONL file into custom_samples and re-index."""
        imported = load_json_dataset(json_path)
        existing_map = (
            {f"{s.task.value}::{s.prompt.strip().lower()}": s for s in self.custom_samples}
            if merge
            else {}
        )
        for sample in imported:
            key = f"{sample.task.value}::{sample.prompt.strip().lower()}"
            existing_map[key] = sample
        self.custom_samples = list(existing_map.values())
        self._rebuild_knowledge_index(include_builtin=True)
        return len(imported)

    def _resolve_training_backends(
        self,
        requested: FrameworkBackend | None,
        backends: dict[str, BaseNeuralBackend],
    ) -> list[BaseNeuralBackend]:
        available = [b for b in backends.values() if b.health().available]
        if not available:
            raise RuntimeError("No deep learning backend is currently available for training.")

        if requested is None or requested == FrameworkBackend.HYBRID:
            return available

        target = backends.get(requested.value)
        if target is not None and target.health().available:
            return [target]
        return [available[0]]

    def train(
        self,
        request: TrainingRequest,
        backends: dict[str, BaseNeuralBackend],
        models: dict[ModelTier, BaseAIModel],
    ) -> TrainingResult:
        """Train selected neural backend(s) on built-in and custom labeled examples."""
        if request.samples:
            existing_map = {
                f"{s.task.value}::{s.prompt.strip().lower()}": s for s in self.custom_samples
            }
            for sample in request.samples:
                key = f"{sample.task.value}::{sample.prompt.strip().lower()}"
                existing_map[key] = sample
            self.custom_samples = list(existing_map.values())

        self._rebuild_knowledge_index(include_builtin=request.include_builtin_dataset or not self.custom_samples)
        active_samples = (
            list(self.knowledge_samples)
            if request.include_builtin_dataset
            else (list(self.custom_samples) or list(BUILTIN_TRAINING_SAMPLES))
        )

        # Ensure class diversity is preserved if custom dataset only covers 1-2 intents
        if len(active_samples) < 4:
            active_samples.extend(BUILTIN_TRAINING_SAMPLES[: 4 - len(active_samples)])

        encoded_examples: list[tuple[list[int], int]] = [
            (self.tokenizer.encode(sample.prompt, max_length=32), self._intent_id(sample.intent))
            for sample in active_samples
        ]

        spec = TIER_SPECS[request.tier]
        target_backends = self._resolve_training_backends(request.backend, backends)
        trained_stats: list[BackendTrainingStats] = []

        with LatencyTimer() as timer:
            for backend in target_backends:
                ckpt_path = self._checkpoint_file(backend.name, request.tier) if request.save_checkpoint else None
                outcome = backend.train_on_examples(
                    examples=encoded_examples,
                    hidden_dim=spec.hidden_dim,
                    num_layers=spec.num_layers,
                    vocab_size=spec.vocab_size,
                    epochs=request.epochs,
                    learning_rate=request.learning_rate,
                    checkpoint_path=ckpt_path,
                )
                trained_stats.append(
                    BackendTrainingStats(
                        backend=outcome.backend,
                        device=outcome.device,
                        epochs=outcome.epochs,
                        initial_loss=outcome.initial_loss,
                        final_loss=outcome.final_loss,
                        accuracy=outcome.accuracy,
                        samples_seen=outcome.samples_seen,
                        parameter_count=outcome.parameter_count,
                        checkpoint_path=outcome.checkpoint_path,
                    )
                )

        learned_intents = sorted({sample.intent for sample in active_samples})
        result = TrainingResult(
            training_id=uuid4().hex,
            tier=request.tier,
            model_id=models[request.tier].spec.model_id,
            dataset_size=len(active_samples),
            learned_intents=learned_intents,
            backends_trained=trained_stats,
            checkpoint_path=str(self.checkpoint_dir) if request.save_checkpoint else None,
            duration_ms=timer.elapsed_ms,
        )
        self.last_training = result

        if request.save_checkpoint:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            serialized_kb = (
                json.dumps(
                    [s.model_dump(mode="json") for s in self.custom_samples],
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                if len(self.custom_samples) > 250
                else json.dumps(
                    [s.model_dump(mode="json") for s in self.custom_samples],
                    indent=2,
                    ensure_ascii=False,
                )
            )
            (self.checkpoint_dir / self.KNOWLEDGE_FILENAME).write_text(
                serialized_kb,
                encoding="utf-8",
            )
            (self.checkpoint_dir / self.STATE_FILENAME).write_text(
                result.model_dump_json(indent=2),
                encoding="utf-8",
            )

        return result

    def status(self) -> TrainingStatusResponse:
        """Return summary metrics of learned datasets and saved checkpoints."""
        return TrainingStatusResponse(
            trained=self.last_training is not None,
            dataset_size=len(self.knowledge_samples),
            learned_intents=sorted({s.intent for s in self.knowledge_samples}),
            checkpoint_dir=str(self.checkpoint_dir),
            last_training=self.last_training,
        )

    def train_all(
        self,
        request: TrainingRequest,
        backends: dict[str, BaseNeuralBackend],
        models: dict[ModelTier, BaseAIModel],
    ) -> AllTiersTrainingResult:
        """Train Flash, Pro, and Advance model tiers across selected neural backends."""
        tier_results: list[TrainingResult] = []
        with LatencyTimer() as timer:
            for tier in (ModelTier.FLASH, ModelTier.PRO, ModelTier.ADVANCE):
                tier_req = request.model_copy(update={"tier": tier})
                tier_results.append(self.train(tier_req, backends, models))

        latest = tier_results[-1]
        return AllTiersTrainingResult(
            training_id=uuid4().hex,
            dataset_size=latest.dataset_size,
            learned_intents=latest.learned_intents,
            tier_results=tier_results,
            total_duration_ms=timer.elapsed_ms,
        )

    def evaluate(
        self,
        request: EvaluationRequest,
        models: dict[ModelTier, BaseAIModel],
    ) -> EvaluationResult:
        """Evaluate intent prediction, neural confidence, and sample retrieval without mutating weights."""
        model = models[request.tier]
        encoding = model.run_neural_encoding(
            prompt=request.prompt,
            backend_override=request.backend,
        )
        predicted_intent, intent_conf = self.predict_intent(encoding.latent_vector, request.prompt)
        matched, match_score = self.retrieve_best_match(request.prompt, task=request.task, min_score=0.25)
        expected = request.expected_intent.strip().lower() if request.expected_intent else None
        preview = matched.response[:220] if matched is not None else f"Predicted intent '{predicted_intent}' via {'+'.join(encoding.frameworks_invoked)}."

        return EvaluationResult(
            prompt=request.prompt,
            tier=request.tier,
            predicted_intent=predicted_intent,
            intent_confidence=intent_conf,
            expected_intent=expected,
            intent_matched=(predicted_intent == expected) if expected is not None else None,
            matched_sample_prompt=matched.prompt if matched is not None else None,
            matched_sample_score=match_score,
            confidence_score=encoding.confidence_score,
            frameworks_invoked=encoding.frameworks_invoked,
            generated_preview=preview,
        )

    def list_checkpoints(self) -> list[CheckpointInfo]:
        """Inspect persisted weights and training metadata files on disk."""
        if not self.checkpoint_dir.exists():
            return []
        items: list[CheckpointInfo] = []
        for path in sorted(self.checkpoint_dir.iterdir()):
            if not path.is_file() or path.suffix not in (".pt", ".npz", ".json"):
                continue
            stem_parts = path.stem.split("_", 1)
            backend = stem_parts[0] if len(stem_parts) == 2 and path.suffix in (".pt", ".npz") else "metadata"
            tier = stem_parts[1] if len(stem_parts) == 2 and path.suffix in (".pt", ".npz") else "all"
            stat = path.stat()
            items.append(
                CheckpointInfo(
                    filename=path.name,
                    backend=backend,
                    tier=tier,
                    size_bytes=stat.st_size,
                    path=str(path),
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
        return items

    def reset(self, backends: dict[str, BaseNeuralBackend]) -> dict[str, object]:
        """Remove persisted checkpoints/custom knowledge and reset backend caches."""
        removed = 0
        if self.checkpoint_dir.exists():
            for path in self.checkpoint_dir.iterdir():
                if path.is_file() and path.suffix in (".pt", ".npz", ".json"):
                    path.unlink()
                    removed += 1
        for backend in backends.values():
            backend.clear_cache()
        self.custom_samples = []
        self._rebuild_knowledge_index(include_builtin=True)
        self.last_training = None
        return {
            "reset": True,
            "removed_files": removed,
            "dataset_size": len(self.knowledge_samples),
        }

    def predict_intent(self, latent_vector: list[float], prompt: str) -> tuple[str, float]:
        """Classify prompt intent from trained neural logits blended with lexical confidence."""
        if latent_vector and self.last_training is not None:
            vec = latent_vector[: len(self.intent_labels)]
            max_v = max(vec)
            exps = [math.exp(v - max_v) for v in vec]
            total = sum(exps) or 1.0
            probs = [e / total for e in exps]
            best_idx = max(range(len(probs)), key=lambda i: probs[i])
            if probs[best_idx] >= 0.25:
                return self.intent_labels[best_idx], round(probs[best_idx], 4)

        best_sample, score = self.retrieve_best_match(prompt, min_score=0.18)
        if best_sample is not None:
            return best_sample.intent, round(score, 4)
        return "general", 0.5

    def retrieve_best_match(
        self,
        prompt: str,
        task: TaskType | None = None,
        min_score: float = 0.42,
        require_multiline: bool = False,
        intent_filter: str | None = None,
    ) -> tuple[TrainingSample | None, float]:
        """Find highest-scoring trained or built-in sample matching the prompt."""
        query_tokens = {tok.lower() for tok in self.tokenizer.tokenize(prompt) if len(tok) > 1 or tok.isalnum()}
        if not query_tokens:
            return None, 0.0

        lookup_tokens = [tok for tok in query_tokens if tok not in _STOPWORDS] or list(query_tokens)
        candidate_indices: set[int] = set()
        for tok in lookup_tokens:
            hits = self._token_index.get(tok)
            if hits:
                candidate_indices.update(hits)
        if not candidate_indices and len(lookup_tokens) < len(query_tokens):
            for tok in query_tokens:
                hits = self._token_index.get(tok)
                if hits:
                    candidate_indices.update(hits)
        if not candidate_indices:
            return None, 0.0

        best_sample: TrainingSample | None = None
        best_score = 0.0
        prompt_lower = prompt.strip().lower()

        for idx in candidate_indices:
            sample, cand_tokens, cand_lower, is_custom = self._indexed_entries[idx]
            if task is not None and sample.task != task:
                continue
            if intent_filter is not None and sample.intent != intent_filter:
                continue
            if require_multiline and not is_custom and "\n" not in sample.response:
                continue
            if not cand_tokens:
                continue
            overlap = len(query_tokens & cand_tokens)
            if overlap == 0:
                continue
            union = len(query_tokens | cand_tokens)
            jaccard = overlap / max(1, union)
            recall = overlap / max(1, min(len(query_tokens), len(cand_tokens)))
            score = 0.45 * jaccard + 0.55 * recall
            if prompt_lower == cand_lower:
                score = 1.0
            elif is_custom:
                score = min(1.0, score + 0.08)

            if score > best_score:
                best_score = score
                best_sample = sample

        if best_sample is not None and best_score >= min_score:
            return best_sample, round(best_score, 4)
        return None, 0.0

