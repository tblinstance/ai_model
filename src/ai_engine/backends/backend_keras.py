"""Keras 3 neural backend providing high-level sequential/functional models."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
if "CUDA_VISIBLE_DEVICES" not in os.environ and not Path("/dev/nvidiactl").exists():
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
if "KERAS_BACKEND" not in os.environ:
    if importlib.util.find_spec("torch") is not None:
        os.environ["KERAS_BACKEND"] = "torch"
    elif importlib.util.find_spec("tensorflow") is not None:
        os.environ["KERAS_BACKEND"] = "tensorflow"
    else:
        os.environ["KERAS_BACKEND"] = "numpy"

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
    import keras
except Exception:  # pragma: no cover
    keras = None  # type: ignore[assignment]


class KerasBackend(BaseNeuralBackend):
    """Keras 3 multi-backend model execution layer."""

    name = "keras"

    def __init__(self, device_preference: str = "auto") -> None:
        self.device_preference = device_preference
        self._models: dict[tuple[int, int, int], object] = {}

    def health(self) -> BackendHealth:
        if keras is None:
            return BackendHealth(name=self.name, available=False, version="not-installed", device="none")
        active_backend = keras.backend.backend()
        return BackendHealth(
            name=self.name,
            available=True,
            version=keras.__version__,
            device="cpu" if self.device_preference == "cpu" else active_backend,
            details={"keras_backend": active_backend},
        )

    def _get_model(self, vocab_size: int, hidden_dim: int, num_layers: int) -> object:
        key = (vocab_size, hidden_dim, num_layers)
        if key not in self._models:
            keras.utils.set_random_seed(77 + hidden_dim + num_layers)
            layers_list: list[object] = [
                keras.layers.Embedding(input_dim=vocab_size, output_dim=hidden_dim, mask_zero=True),
                keras.layers.GlobalAveragePooling1D(),
            ]
            for _ in range(max(1, num_layers)):
                layers_list.append(keras.layers.Dense(hidden_dim, activation="gelu"))
            layers_list.append(keras.layers.Dense(16))
            model = keras.Sequential(layers_list)
            _ = model(np.array([[1, 2, 3]], dtype=np.int32), training=False)
            self._models[key] = model
        return self._models[key]

    def encode_tokens(
        self,
        token_ids: list[int],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        seed: int | None = None,
    ) -> BackendResult:
        if keras is None:
            raise RuntimeError("Keras is not installed.")
        model = self._get_model(vocab_size, hidden_dim, num_layers)
        safe_ids = [max(0, min(vocab_size - 1, tid)) for tid in token_ids] or [1]
        arr = np.array([safe_ids], dtype=np.int32)
        out = model(arr, training=False)  # type: ignore[operator]
        out_np = np.asarray(keras.ops.convert_to_numpy(out), dtype=np.float32)[0]

        norm = float(np.linalg.norm(out_np))
        exp = np.exp(out_np - np.max(out_np))
        probs = exp / np.sum(exp)
        confidence = round(min(0.99, max(0.56, 0.56 + float(np.max(probs)) * 2.1)), 4)

        return BackendResult(
            backend=self.name,
            device=keras.backend.backend(),
            parameter_count=int(model.count_params()),  # type: ignore[attr-defined]
            latent_vector=[round(float(v), 5) for v in out_np.tolist()],
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
        if keras is None:
            raise RuntimeError("Keras is not installed.")
        seed_val = seed if seed is not None else (sum(token_ids) % 100000)
        rng = np.random.default_rng(seed_val)
        base = rng.normal(0.0, 0.5, size=(1, 16, 16, channels)).astype(np.float32)
        upsample = keras.layers.Resizing(height, width, interpolation="bilinear")
        out = np.asarray(keras.ops.convert_to_numpy(upsample(base)), dtype=np.float32)[0]
        return np.clip(1.0 / (1.0 + np.exp(-out)), 0.0, 1.0).astype(np.float32)

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
        if keras is None:
            raise RuntimeError("Keras is not installed.")
        model = self._get_model(vocab_size, hidden_dim, num_layers)
        x_np, y_np = prepare_training_batch(examples, seq_len=32, vocab_size=vocab_size)
        x_in = x_np.astype(np.int32)
        y_in = y_np.astype(np.int32)

        loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        init_logits = np.asarray(keras.ops.convert_to_numpy(model(x_in, training=False)), dtype=np.float32)  # type: ignore[operator]
        initial_loss = float(keras.ops.convert_to_numpy(loss_fn(y_in, init_logits)))

        opt_lr = effective_learning_rate(learning_rate, hidden_dim, num_layers, backend_scale=0.65)
        model.compile(  # type: ignore[attr-defined]
            optimizer=keras.optimizers.Adam(learning_rate=opt_lr, clipnorm=1.5),
            loss=loss_fn,
            metrics=["accuracy"],
        )
        model.fit(  # type: ignore[attr-defined]
            x_in,
            y_in,
            epochs=epochs,
            batch_size=adaptive_batch_size(len(examples)),
            verbose=0,
        )

        final_logits = np.asarray(keras.ops.convert_to_numpy(model(x_in, training=False)), dtype=np.float32)  # type: ignore[operator]
        final_loss = float(keras.ops.convert_to_numpy(loss_fn(y_in, final_logits)))
        preds = np.argmax(final_logits, axis=-1)
        accuracy = float(np.mean(preds == y_in))

        saved_path: str | None = None
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            arrays = {f"w_{idx}": np.asarray(w) for idx, w in enumerate(model.get_weights())}  # type: ignore[attr-defined]
            np.savez_compressed(checkpoint_path, **arrays)
            saved_path = str(checkpoint_path)

        return BackendTrainingOutcome(
            backend=self.name,
            device=keras.backend.backend(),
            epochs=epochs,
            initial_loss=round(initial_loss, 5),
            final_loss=round(final_loss, 5),
            accuracy=round(accuracy, 4),
            samples_seen=len(examples) * epochs,
            parameter_count=int(model.count_params()),  # type: ignore[attr-defined]
            checkpoint_path=saved_path,
        )

    def load_weights(
        self,
        checkpoint_path: Path,
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
    ) -> bool:
        if keras is None or not checkpoint_path.exists():
            return False
        model = self._get_model(vocab_size, hidden_dim, num_layers)
        with np.load(checkpoint_path, allow_pickle=False) as archive:
            current = model.get_weights()  # type: ignore[attr-defined]
            if len(archive.files) != len(current):
                return False
            loaded = [archive[f"w_{idx}"] for idx in range(len(current))]
            if any(c.shape != w.shape for c, w in zip(current, loaded)):
                return False
            model.set_weights(loaded)  # type: ignore[attr-defined]
        return True

    def clear_cache(self) -> None:
        self._models.clear()
