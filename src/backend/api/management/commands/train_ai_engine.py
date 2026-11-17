"""CLI management command to train ai_engine models directly from Django backend."""

from __future__ import annotations

from pathlib import Path
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import TrainingRun, TrainingSampleRecord


class Command(BaseCommand):
    """Train all or selected ai_engine tiers and neural backends using PostgreSQL + built-in datasets."""

    help = "Train ai_engine models across NumPy, PyTorch, TensorFlow, and Keras and log runs in PostgreSQL."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--tier", choices=["flash", "pro", "advance"], default="flash")
        parser.add_argument("--all-tiers", action="store_true", help="Train Flash, Pro, and Advance tiers.")
        parser.add_argument(
            "--backend",
            choices=["numpy", "pytorch", "tensorflow", "keras", "hybrid"],
            default="hybrid",
        )
        parser.add_argument("--epochs", type=int, default=8)
        parser.add_argument("--lr", type=float, default=0.012)
        parser.add_argument(
            "--task",
            choices=["all", "chat", "code", "images", "video", "audio"],
            default="all",
            help="Optional focus audit task (default: all tasks).",
        )
        parser.add_argument("--reset", action="store_true", help="Clear existing checkpoints before training.")
        parser.add_argument(
            "--txt",
            "--text-file",
            dest="text_file",
            type=str,
            default="",
            help="Path to external raw .txt file (e.g. 1GB corpus) to load and train on.",
        )
        parser.add_argument(
            "--max-txt-samples",
            type=int,
            default=50000,
            help="Maximum number of samples to parse from the text file.",
        )

    def handle(self, *args, **options) -> None:
        curr = Path(__file__).resolve()
        for cand in (curr.parents[4], curr.parents[3].parent, curr.parents[3]):
            if (cand / "ai_engine").is_dir() and str(cand) not in sys.path:
                sys.path.insert(0, str(cand))

        from ai_engine import AIEngineRouter, FrameworkBackend, ModelTier, TaskType, TrainingRequest, TrainingSample
        from ai_engine.training.dataset import dataset_summary

        summary = dataset_summary()
        self.stdout.write(
            f"Corpus loaded: {summary['sample_count']} samples "
            f"(chat: {summary['task_counts'].get('chat', 0)}, "
            f"code: {summary['task_counts'].get('code', 0)}, "
            f"images: {summary['task_counts'].get('images', 0)}, "
            f"video: {summary['task_counts'].get('video', 0)}, "
            f"audio: {summary['task_counts'].get('audio', 0)})"
        )
        db_samples = []
        try:
            db_samples = [
                TrainingSample(
                    prompt=rec.prompt[:4000],
                    response=rec.response[:16000],
                    intent=rec.intent or "general",
                    task=TaskType(rec.task or "chat"),
                )
                for rec in TrainingSampleRecord.objects.filter(is_active=True)[:25000]
            ]
        except Exception:
            pass
        if options.get("text_file"):
            txt_path = Path(options["text_file"]).expanduser().resolve()
            if txt_path.exists():
                from ai_engine.training.dataset import load_txt_dataset
                txt_samples = load_txt_dataset(
                    txt_path,
                    max_samples=options.get("max_txt_samples", 50000),
                    intent="text_corpus",
                    task=TaskType.CHAT if options["task"] == "all" else TaskType(options["task"]),
                )
                self.stdout.write(
                    f"Loaded {len(txt_samples)} samples from raw text file: {txt_path}"
                )
                db_samples.extend(txt_samples)
            else:
                self.stderr.write(f"Warning: text file not found: {txt_path}")
        router = AIEngineRouter()
        if options["reset"]:
            router.reset_training()
        req = TrainingRequest(
            tier=ModelTier(options["tier"]),
            backend=FrameworkBackend(options["backend"]),
            epochs=options["epochs"],
            learning_rate=options["lr"],
            include_builtin_dataset=True,
            samples=db_samples,
            save_checkpoint=True,
        )

        actor = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        if options["all_tiers"]:
            tier_results = []
            total_ms = 0.0
            for tier in (ModelTier.FLASH, ModelTier.PRO, ModelTier.ADVANCE):
                self.stdout.write(
                    f"Training tier={tier.value} (backend={options['backend']}, task={options['task']}, epochs={options['epochs']}, samples={len(router.registry.trainer.knowledge_samples) + len(db_samples)})..."
                )
                self.stdout.flush()
                tier_req = req.model_copy(update={"tier": tier})
                tr = router.train(tier_req)
                tier_results.append(tr)
                total_ms += tr.duration_ms
                try:
                    TrainingRun.objects.create(
                        user=actor,
                        training_id=tr.training_id,
                        scope="all",
                        tier=tr.tier.value,
                        backend=options["backend"],
                        epochs=options["epochs"],
                        learning_rate=options["lr"],
                        dataset_size=tr.dataset_size,
                        learned_intents=tr.learned_intents,
                        backends_trained=[b.model_dump(mode="json") for b in tr.backends_trained],
                        duration_ms=tr.duration_ms,
                        status="completed",
                    )
                except Exception:
                    pass
                summary_parts = ", ".join(
                    f"{b.backend}:{b.final_loss:.4f}/{b.accuracy:.0%}" for b in tr.backends_trained
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {tier.value} done in {tr.duration_ms:.0f} ms [{summary_parts}]"
                    )
                )
                self.stdout.flush()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Trained ALL tiers ({len(tier_results)} tiers, {tier_results[-1].dataset_size} samples) in {total_ms:.1f} ms."
                )
            )
            if options["task"] == "code":
                for probe_prompt in (
                    "django install tutorial",
                    "django transaction select_for_update",
                    "react mp4 video player component",
                    "postgres select for update credit wallet",
                ):
                    matched, score = router.registry.trainer.retrieve_best_match(
                        probe_prompt, task=TaskType.CODE, min_score=0.55, require_multiline=True
                    )
                    self.stdout.write(
                        f"  [code eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                    )
            elif options["task"] == "video":
                for probe_prompt in (
                    "create 10-minute vortex MP4 cosmic nebula",
                    "render 12-minute tidal ripple ocean bioluminescent MP4",
                    "animate 10-minute cyberpunk neon laser grid sweep MP4",
                    "train carton video playful bouncing character motion vibrant cel-shaded",
                    "create 10-minute cartoon animated video comic pop art ink sequence",
                    "create animated gif video orbital rings harmonic oscillation",
                ):
                    matched, score = router.registry.trainer.retrieve_best_match(
                        probe_prompt, task=TaskType.VIDEO, min_score=0.35
                    )
                    self.stdout.write(
                        f"  [video eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                    )
            elif options["task"] == "audio":
                for probe_prompt in (
                    "synthesize voice speech for welcoming users to ai model studio platform",
                    "transcribe meeting recording multilingual speech recognition whisper timestamps",
                    "analyze audio waveform spectrogram duration sample rate librosa soundfile",
                    "synthesize bangla bengali voice speech bkash nagad payment alert",
                ):
                    matched, score = router.registry.trainer.retrieve_best_match(
                        probe_prompt, task=TaskType.AUDIO, min_score=0.35
                    )
                    self.stdout.write(
                        f"  [audio eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                    )
            elif options["task"] == "images":
                for probe_prompt in (
                    "draw render generate image illustration portrait logo artwork",
                    "photorealistic portrait of a female software engineer",
                ):
                    matched, score = router.registry.trainer.retrieve_best_match(
                        probe_prompt, task=TaskType.IMAGES, min_score=0.35
                    )
                    self.stdout.write(
                        f"  [images eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                    )
            return

        single = router.train(req)
        try:
            TrainingRun.objects.create(
                user=actor,
                training_id=single.training_id,
                scope="single",
                tier=single.tier.value,
                backend=options["backend"],
                epochs=options["epochs"],
                learning_rate=options["lr"],
                dataset_size=single.dataset_size,
                learned_intents=single.learned_intents,
                backends_trained=[b.model_dump(mode="json") for b in single.backends_trained],
                duration_ms=single.duration_ms,
                status="completed",
            )
        except Exception:
            pass
        self.stdout.write(
            self.style.SUCCESS(
                f"Trained {single.tier.value} across {len(single.backends_trained)} backend(s) in {single.duration_ms} ms."
            )
        )
        if options["task"] == "video":
            for probe_prompt in (
                "create 10-minute vortex MP4 cosmic nebula",
                "render 12-minute tidal ripple ocean bioluminescent MP4",
                "animate 10-minute cyberpunk neon laser grid sweep MP4",
                "train carton video playful bouncing character motion vibrant cel-shaded",
                "create 10-minute cartoon animated video comic pop art ink sequence",
                "create animated gif video orbital rings harmonic oscillation",
            ):
                matched, score = router.registry.trainer.retrieve_best_match(
                    probe_prompt, task=TaskType.VIDEO, min_score=0.35
                )
                self.stdout.write(
                    f"  [video eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                )
        elif options["task"] == "audio":
            for probe_prompt in (
                "synthesize voice speech for welcoming users to ai model studio platform",
                "transcribe meeting recording multilingual speech recognition whisper timestamps",
                "analyze audio waveform spectrogram duration sample rate librosa soundfile",
                "synthesize bangla bengali voice speech bkash nagad payment alert",
            ):
                matched, score = router.registry.trainer.retrieve_best_match(
                    probe_prompt, task=TaskType.AUDIO, min_score=0.35
                )
                self.stdout.write(
                    f"  [audio eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                )
        elif options["task"] == "images":
            for probe_prompt in (
                "draw render generate image illustration portrait logo artwork",
                "photorealistic portrait of a female software engineer",
            ):
                matched, score = router.registry.trainer.retrieve_best_match(
                    probe_prompt, task=TaskType.IMAGES, min_score=0.35
                )
                self.stdout.write(
                    f"  [images eval] {probe_prompt!r} -> score={score:.2f}, intent={matched.intent if matched else 'fallback'}"
                )
