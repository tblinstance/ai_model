"""TensorFlow neural backend providing dense/attention graph scoring and synthesis."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
if "CUDA_VISIBLE_DEVICES" not in os.environ and not Path("/dev/nvidiactl").exists():
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

from .backend_base import (
    BackendHealth,
    BackendResult,
    BackendTrainingOutcome,
    BaseNeuralBackend,
    adaptive_batch_size,
    effective_learning_rate,
    prepare_training_batch,
)

try:
    import tensorflow as tf
except ImportError:  # pragma: no cover
    tf = None  # type: ignore[assignment]


class TensorFlowBackend(BaseNeuralBackend):
    """TensorFlow execution backend supporting tensor graph forward inference."""

    name = "tensorflow"

    def __init__(self, device_preference: str = "auto") -> None:
        self.device_preference = device_preference
        self._weights_cache: dict[tuple[int, int, int], dict[str, object]] = {}

    def _resolve_device(self) -> str:
        if tf is None:
            return "unavailable"
        if self.device_preference == "cpu":
            return "cpu"
        gpus = tf.config.list_physical_devices("GPU")
        return "gpu" if gpus else "cpu"

    def health(self) -> BackendHealth:
        if tf is None:
            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            return BackendHealth(
                name=self.name,
                available=False,
                version="not-installed",
                device="none",
                details={
                    "fallback_backend": "pytorch",
                    "python_version": py_ver,
                    "reason": (
                        f"TensorFlow is not installed in Python {py_ver}; "
                        "requests automatically fall back to PyTorch/Keras."
                    ),
                },
            )
        gpus = tf.config.list_physical_devices("GPU")
        return BackendHealth(
            name=self.name,
            available=True,
            version=tf.__version__,
            device=self._resolve_device(),
            details={"gpu_count": len(gpus)},
        )

    def _get_weights(self, vocab_size: int, hidden_dim: int, num_layers: int) -> dict[str, object]:
        key = (vocab_size, hidden_dim, num_layers)
        if key not in self._weights_cache:
            rng = tf.random.Generator.from_seed(101 + hidden_dim + num_layers)
            emb = tf.Variable(
                rng.normal(shape=(vocab_size, hidden_dim), stddev=0.08),
                trainable=True,
                name="emb",
            )
            layers = [
                (
                    tf.Variable(
                        rng.normal(shape=(hidden_dim, hidden_dim), stddev=0.09),
                        trainable=True,
                        name=f"layer_{idx}_w",
                    ),
                    tf.Variable(
                        tf.zeros((hidden_dim,), dtype=tf.float32),
                        trainable=True,
                        name=f"layer_{idx}_b",
                    ),
                )
                for idx in range(max(1, num_layers))
            ]
            proj = tf.Variable(
                rng.normal(shape=(hidden_dim, 16), stddev=0.1),
                trainable=True,
                name="proj",
            )
            self._weights_cache[key] = {"emb": emb, "layers": layers, "proj": proj}
        return self._weights_cache[key]

    @staticmethod
    def _trainable_variables(weights: dict[str, object]) -> list[object]:
        vars_list: list[object] = [weights["emb"]]
        for w, b in weights["layers"]:  # type: ignore[attr-defined]
            vars_list.extend([w, b])
        vars_list.append(weights["proj"])
        return vars_list

    @staticmethod
    def _forward_logits(ids_batch: object, weights: dict[str, object]) -> tuple[object, object]:
        x = tf.gather(weights["emb"], ids_batch)  # type: ignore[arg-type]
        mask = tf.cast(tf.not_equal(ids_batch, 0), tf.float32)[..., tf.newaxis]
        denom = tf.maximum(tf.reduce_sum(mask, axis=1), 1.0)
        x = tf.reduce_sum(x * mask, axis=1) / denom
        for w, b in weights["layers"]:  # type: ignore[attr-defined]
            x = tf.nn.gelu(tf.matmul(x, w) + b) + x * 0.25
        logits = tf.matmul(x, weights["proj"])  # type: ignore[arg-type]
        return x, logits

    def encode_tokens(
        self,
        token_ids: list[int],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        seed: int | None = None,
    ) -> BackendResult:
        if tf is None:
            raise RuntimeError("TensorFlow is not installed.")
        weights = self._get_weights(vocab_size, hidden_dim, num_layers)
        safe_ids = [max(1, min(vocab_size - 1, tid)) for tid in token_ids] or [1]
        ids_tensor = tf.constant([safe_ids], dtype=tf.int32)

        x, logits = self._forward_logits(ids_tensor, weights)
        norm = float(tf.norm(x).numpy())
        probs = tf.nn.softmax(logits, axis=-1)
        max_prob = float(tf.reduce_max(probs).numpy())

        param_count = vocab_size * hidden_dim + num_layers * (hidden_dim * hidden_dim + hidden_dim) + hidden_dim * 16
        latent_vec = [round(float(v), 5) for v in tf.squeeze(logits, axis=0).numpy().tolist()]
        confidence = round(min(0.99, max(0.58, 0.58 + max_prob * 2.1)), 4)

        return BackendResult(
            backend=self.name,
            device=self._resolve_device(),
            parameter_count=param_count,
            latent_vector=latent_vec,
            latent_norm=round(norm, 4),
            confidence_score=confidence,
        )

    def synthesize_spatial_field(
        self,
        token_ids: list[int],
        width: int,
        height: int,
        channels: int = 3,
        seed: int | None = None,
    ) -> np.ndarray:
        if tf is None:
            raise RuntimeError("TensorFlow is not installed.")
        seed_val = seed if seed is not None else (sum(token_ids) % 100000)
        rng = tf.random.Generator.from_seed(seed_val)
        latent_h, latent_w = max(8, height // 12), max(8, width // 12)
        noise = rng.normal(shape=(1, latent_h, latent_w, channels), stddev=0.65)
        resized = tf.image.resize(noise, size=(height, width), method="bicubic")
        field = tf.math.sigmoid(resized)
        return np.clip(field[0].numpy(), 0.0, 1.0).astype(np.float32)

    def train_on_examples(
        self,
        examples: list[tuple[list[int], int]],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        epochs: int = 6,
        learning_rate: float = 0.01,
        checkpoint_path: Path | None = None,
    ) -> BackendTrainingOutcome:
        if tf is None:
            raise RuntimeError("TensorFlow is not installed.")
        weights = self._get_weights(vocab_size, hidden_dim, num_layers)
        trainable_vars = self._trainable_variables(weights)
        x_np, y_np = prepare_training_batch(examples, seq_len=32, vocab_size=vocab_size)
        x_t = tf.constant(x_np, dtype=tf.int32)
        y_t = tf.constant(y_np, dtype=tf.int32)

        def _batch_loss_and_acc(bx: object, by: object) -> tuple[object, float]:
            _, logits = self._forward_logits(bx, weights)
            loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=by, logits=logits))
            preds = tf.argmax(logits, axis=-1, output_type=tf.int32)
            acc = float(tf.reduce_mean(tf.cast(tf.equal(preds, by), tf.float32)).numpy())
            return loss, acc

        init_loss_t, _ = _batch_loss_and_acc(x_t, y_t)
        initial_loss = float(init_loss_t.numpy())

        m_slots = [tf.zeros_like(v) for v in trainable_vars]
        v_slots = [tf.zeros_like(v) for v in trainable_vars]
        beta1, beta2, eps = 0.9, 0.999, 1e-7
        step = 0
        opt_lr = effective_learning_rate(learning_rate, hidden_dim, num_layers, backend_scale=0.65)
        batch_size = adaptive_batch_size(len(examples))

        for _ in range(epochs):
            perm = np.random.permutation(len(examples))
            for start in range(0, len(examples), batch_size):
                idx = perm[start : start + batch_size]
                bx = tf.constant(x_np[idx], dtype=tf.int32)
                by = tf.constant(y_np[idx], dtype=tf.int32)
                with tf.GradientTape() as tape:
                    _, logits = self._forward_logits(bx, weights)
                    loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=by, logits=logits))
                raw_grads = [
                    tf.convert_to_tensor(g, dtype=tf.float32) if g is not None else tf.zeros_like(v)
                    for g, v in zip(tape.gradient(loss, trainable_vars), trainable_vars)
                ]
                clipped_grads, _ = tf.clip_by_global_norm(raw_grads, 1.5)
                step += 1
                lr_t = opt_lr * ((1.0 - beta2**step) ** 0.5) / (1.0 - beta1**step)
                for i, (var, g) in enumerate(zip(trainable_vars, clipped_grads)):
                    m_slots[i] = beta1 * m_slots[i] + (1.0 - beta1) * g
                    v_slots[i] = beta2 * v_slots[i] + (1.0 - beta2) * tf.square(g)
                    var.assign_sub(lr_t * m_slots[i] / (tf.sqrt(v_slots[i]) + eps))  # type: ignore[attr-defined]

        final_loss_t, accuracy = _batch_loss_and_acc(x_t, y_t)
        final_loss = float(final_loss_t.numpy())

        saved_path: str | None = None
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            arrays = {f"w_{idx}": v.numpy() for idx, v in enumerate(trainable_vars)}  # type: ignore[attr-defined]
            np.savez_compressed(checkpoint_path, **arrays)
            saved_path = str(checkpoint_path)

        param_count = vocab_size * hidden_dim + num_layers * (hidden_dim * hidden_dim + hidden_dim) + hidden_dim * 16
        return BackendTrainingOutcome(
            backend=self.name,
            device=self._resolve_device(),
            epochs=epochs,
            initial_loss=round(initial_loss, 5),
            final_loss=round(final_loss, 5),
            accuracy=round(accuracy, 4),
            samples_seen=len(examples) * epochs,
            parameter_count=param_count,
            checkpoint_path=saved_path,
        )

    def load_weights(
        self,
        checkpoint_path: Path,
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
    ) -> bool:
        if tf is None or not checkpoint_path.exists():
            return False
        weights = self._get_weights(vocab_size, hidden_dim, num_layers)
        trainable_vars = self._trainable_variables(weights)
        with np.load(checkpoint_path, allow_pickle=False) as archive:
            if len(archive.files) != len(trainable_vars):
                return False
            for idx, var in enumerate(trainable_vars):
                arr = archive[f"w_{idx}"]
                if tuple(var.shape) != tuple(arr.shape):  # type: ignore[attr-defined]
                    return False
                var.assign(arr)  # type: ignore[attr-defined]
        return True

    def clear_cache(self) -> None:
        self._weights_cache.clear()

