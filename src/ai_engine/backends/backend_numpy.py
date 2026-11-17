"""Pure-CPU vectorized NumPy neural backend (default fast background engine)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .backend_base import (
    BackendHealth,
    BackendResult,
    BackendTrainingOutcome,
    BaseNeuralBackend,
    adaptive_batch_size,
    effective_learning_rate,
    prepare_training_batch,
)

_NUM_INTENTS = 16
_SEQ_LEN = 32


class NumPyBackend(BaseNeuralBackend):
    """Lightweight vectorized NumPy neural backend for ultra-fast CPU inference & training."""

    name: str = "numpy"

    def __init__(self, device_preference: str = "cpu") -> None:
        self.device_preference = "cpu"
        self._weights: dict[tuple[int, int, int], dict[str, np.ndarray]] = {}

    def health(self) -> BackendHealth:
        return BackendHealth(
            name=self.name,
            available=True,
            version=np.__version__,
            device="cpu",
            details={
                "vectorized": True,
                "engine": "numpy-simd",
                "cached_models": len(self._weights),
            },
        )

    def _expected_shapes(
        self, vocab_size: int, hidden_dim: int, num_layers: int
    ) -> dict[str, tuple[int, ...]]:
        shapes: dict[str, tuple[int, ...]] = {
            "emb": (vocab_size, hidden_dim),
            "w_out": (hidden_dim, _NUM_INTENTS),
            "b_out": (_NUM_INTENTS,),
        }
        for idx in range(num_layers):
            shapes[f"w_{idx}"] = (hidden_dim, hidden_dim)
            shapes[f"b_{idx}"] = (hidden_dim,)
        return shapes

    def _init_weights(
        self, vocab_size: int, hidden_dim: int, num_layers: int, seed: int | None = None
    ) -> dict[str, np.ndarray]:
        seed_val = (
            42 + vocab_size * 7 + hidden_dim * 13 + num_layers * 31
            if seed is None
            else int(seed)
        )
        rng = np.random.default_rng(seed_val)
        emb_scale = np.float32(1.0 / np.sqrt(float(hidden_dim)))
        hid_scale = np.float32(1.0 / np.sqrt(float(hidden_dim)))
        out_scale = np.float32(1.0 / np.sqrt(float(hidden_dim)))

        weights: dict[str, np.ndarray] = {
            "emb": rng.normal(0.0, emb_scale, size=(vocab_size, hidden_dim)).astype(
                np.float32
            ),
            "w_out": rng.normal(0.0, out_scale, size=(hidden_dim, _NUM_INTENTS)).astype(
                np.float32
            ),
            "b_out": np.zeros((_NUM_INTENTS,), dtype=np.float32),
        }
        weights["emb"][0] = 0.0
        for idx in range(num_layers):
            weights[f"w_{idx}"] = rng.normal(
                0.0, hid_scale, size=(hidden_dim, hidden_dim)
            ).astype(np.float32)
            weights[f"b_{idx}"] = np.zeros((hidden_dim,), dtype=np.float32)
        return weights

    def _get_or_init_weights(
        self, vocab_size: int, hidden_dim: int, num_layers: int
    ) -> dict[str, np.ndarray]:
        key = (vocab_size, hidden_dim, num_layers)
        cached = self._weights.get(key)
        if cached is not None:
            return cached
        weights = self._init_weights(vocab_size, hidden_dim, num_layers)
        self._weights[key] = weights
        return weights

    @staticmethod
    def _parameter_count(weights: dict[str, np.ndarray]) -> int:
        return int(sum(arr.size for arr in weights.values()))

    @staticmethod
    def _sequence_weights(x_batch: np.ndarray) -> np.ndarray:
        mask = (x_batch > 0).astype(np.float32)
        pos_decay = (1.0 - 0.015 * np.arange(x_batch.shape[1], dtype=np.float32))[
            None, :
        ]
        weighted = mask * pos_decay
        denom = np.maximum(weighted.sum(axis=1, keepdims=True), 1.0)
        return (weighted / denom)[:, :, None]

    def _forward(
        self,
        x_batch: np.ndarray,
        weights: dict[str, np.ndarray],
        num_layers: int,
    ) -> tuple[np.ndarray, dict[str, object]]:
        seq_w = self._sequence_weights(x_batch)
        pooled = (weights["emb"][x_batch] * seq_w).sum(axis=1)

        h = pooled
        layer_inputs: list[np.ndarray] = []
        layer_acts: list[np.ndarray] = []
        for idx in range(num_layers):
            layer_inputs.append(h)
            pre = h @ weights[f"w_{idx}"] + weights[f"b_{idx}"]
            act = np.tanh(pre)
            layer_acts.append(act)
            h = 0.5 * (h + act)

        logits = h @ weights["w_out"] + weights["b_out"]
        cache: dict[str, object] = {
            "seq_w": seq_w,
            "layer_inputs": layer_inputs,
            "layer_acts": layer_acts,
            "h_final": h,
        }
        return logits, cache

    def encode_tokens(
        self,
        token_ids: list[int],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        seed: int | None = None,
    ) -> BackendResult:
        weights = self._get_or_init_weights(vocab_size, hidden_dim, num_layers)
        clipped = [max(1, min(vocab_size - 1, tid)) for tid in token_ids[:_SEQ_LEN]] or [1]
        x_arr = np.zeros((1, _SEQ_LEN), dtype=np.int64)
        x_arr[0, : len(clipped)] = clipped

        logits, _ = self._forward(x_arr, weights, num_layers)
        vec = logits[0].astype(np.float64)

        if seed is not None:
            rng = np.random.default_rng(int(seed))
            vec = vec + rng.normal(0.0, 1e-4, size=vec.shape)

        shifted = vec - np.max(vec)
        probs = np.exp(shifted)
        probs /= np.maximum(np.sum(probs), 1e-9)
        top_prob = float(np.max(probs))
        norm = float(np.linalg.norm(vec))
        confidence = max(0.05, min(0.99, 0.5 + 0.5 * top_prob))

        return BackendResult(
            backend=self.name,
            device="cpu",
            parameter_count=self._parameter_count(weights),
            latent_vector=[round(float(v), 6) for v in vec.tolist()],
            latent_norm=round(norm, 6),
            confidence_score=round(confidence, 6),
        )

    def synthesize_spatial_field(
        self,
        token_ids: list[int],
        width: int,
        height: int,
        channels: int = 3,
        seed: int | None = None,
    ) -> np.ndarray:
        tokens = np.array(token_ids[:64] or [1, 7, 13], dtype=np.float32)
        seed_val = int(seed if seed is not None else int(tokens.sum()) + 17)
        rng = np.random.default_rng(seed_val)

        xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
        ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
        radial = np.sqrt(xs * xs + ys * ys)
        angle = np.arctan2(ys, xs)

        field = np.zeros((height, width, channels), dtype=np.float32)
        mean_tok = float(tokens.mean())
        for ch in range(channels):
            freq_x = 1.6 + ((float(tokens[ch % len(tokens)]) % 19.0) * 0.22)
            freq_y = 1.6 + ((float(tokens[(ch + 1) % len(tokens)]) % 17.0) * 0.24)
            phase = float(rng.uniform(0.0, 2.0 * np.pi)) + (mean_tok * 0.03 * (ch + 1))
            wave_a = np.sin(xs * freq_x + ys * freq_y + phase)
            wave_b = np.cos(radial * (2.4 + 0.35 * ch) - angle * (1.0 + 0.5 * ch) + phase * 0.5)
            raw = 0.55 * wave_a + 0.45 * wave_b
            c_min = float(raw.min())
            c_span = max(float(raw.max()) - c_min, 1e-6)
            field[:, :, ch] = (raw - c_min) / c_span

        return np.clip(field, 0.0, 1.0).astype(np.float32)

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
        x_np, y_np = prepare_training_batch(
            examples, seq_len=_SEQ_LEN, vocab_size=vocab_size
        )
        weights = {
            k: v.copy()
            for k, v in self._init_weights(vocab_size, hidden_dim, num_layers).items()
        }
        lr = effective_learning_rate(
            learning_rate, hidden_dim, num_layers, backend_scale=1.2
        )

        beta1, beta2, eps = 0.9, 0.999, 1e-8
        weight_decay = np.float32(1e-4)
        m_state = {k: np.zeros_like(v) for k, v in weights.items()}
        v_state = {k: np.zeros_like(v) for k, v in weights.items()}

        n_samples = x_np.shape[0]
        full_row_idx = np.arange(n_samples)
        batch_size = adaptive_batch_size(n_samples)
        batch_rng = np.random.default_rng(1337 + hidden_dim + num_layers)

        init_logits, _ = self._forward(x_np, weights, num_layers)
        init_shifted = init_logits - init_logits.max(axis=1, keepdims=True)
        init_exp = np.exp(init_shifted)
        init_probs = init_exp / np.maximum(init_exp.sum(axis=1, keepdims=True), 1e-9)
        initial_loss = float(
            -np.log(np.maximum(init_probs[full_row_idx, y_np], 1e-8)).mean()
        )

        step_epochs = max(1, epochs)
        t_step = 0
        for _ in range(step_epochs):
            perm = batch_rng.permutation(n_samples)
            for start in range(0, n_samples, batch_size):
                idx = perm[start : start + batch_size]
                bx = x_np[idx]
                by = y_np[idx]
                b_n = bx.shape[0]
                b_rows = np.arange(b_n)

                logits, cache = self._forward(bx, weights, num_layers)
                shifted = logits - logits.max(axis=1, keepdims=True)
                exp_logits = np.exp(shifted)
                probs = exp_logits / np.maximum(exp_logits.sum(axis=1, keepdims=True), 1e-9)

                dlogits = probs.copy()
                dlogits[b_rows, by] -= 1.0
                dlogits /= float(b_n)

                grads: dict[str, np.ndarray] = {}
                h_final = cache["h_final"]
                assert isinstance(h_final, np.ndarray)
                grads["w_out"] = h_final.T @ dlogits + weight_decay * weights["w_out"]
                grads["b_out"] = dlogits.sum(axis=0)

                dh = dlogits @ weights["w_out"].T
                layer_inputs = cache["layer_inputs"]
                layer_acts = cache["layer_acts"]
                assert isinstance(layer_inputs, list) and isinstance(layer_acts, list)

                for l_idx in range(num_layers - 1, -1, -1):
                    act = layer_acts[l_idx]
                    h_in = layer_inputs[l_idx]
                    d_pre = (0.5 * dh) * (1.0 - act * act)
                    grads[f"w_{l_idx}"] = h_in.T @ d_pre + weight_decay * weights[f"w_{l_idx}"]
                    grads[f"b_{l_idx}"] = d_pre.sum(axis=0)
                    dh = 0.5 * dh + d_pre @ weights[f"w_{l_idx}"].T

                seq_w = cache["seq_w"]
                assert isinstance(seq_w, np.ndarray)
                grad_emb = np.zeros_like(weights["emb"])
                d_emb_tokens = dh[:, None, :] * seq_w
                np.add.at(grad_emb, bx, d_emb_tokens)
                grad_emb[0] = 0.0
                grads["emb"] = grad_emb

                # Global gradient norm clip to keep deep tiers bounded
                grad_norm = float(
                    np.sqrt(sum(float(np.sum(g * g)) for g in grads.values()))
                )
                clip_scale = 5.0 / grad_norm if grad_norm > 5.0 else 1.0

                t_step += 1
                b1_corr = 1.0 - (beta1**t_step)
                b2_corr = 1.0 - (beta2**t_step)
                for key, grad in grads.items():
                    g = grad * np.float32(clip_scale)
                    m_state[key] = beta1 * m_state[key] + (1.0 - beta1) * g
                    v_state[key] = beta2 * v_state[key] + (1.0 - beta2) * (g * g)
                    m_hat = m_state[key] / np.float32(b1_corr)
                    v_hat = v_state[key] / np.float32(b2_corr)
                    weights[key] = weights[key] - np.float32(lr) * (
                        m_hat / (np.sqrt(v_hat) + np.float32(eps))
                    )
                weights["emb"][0] = 0.0

        final_logits, _ = self._forward(x_np, weights, num_layers)
        final_shifted = final_logits - final_logits.max(axis=1, keepdims=True)
        final_exp = np.exp(final_shifted)
        final_probs = final_exp / np.maximum(final_exp.sum(axis=1, keepdims=True), 1e-9)
        final_loss = float(-np.log(np.maximum(final_probs[full_row_idx, y_np], 1e-8)).mean())
        accuracy = float((final_logits.argmax(axis=1) == y_np).mean())

        self._weights[(vocab_size, hidden_dim, num_layers)] = weights

        saved_path: str | None = None
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(checkpoint_path, **weights)
            saved_path = str(checkpoint_path)

        return BackendTrainingOutcome(
            backend=self.name,
            device="cpu",
            epochs=step_epochs,
            initial_loss=round(initial_loss, 6),
            final_loss=round(final_loss, 6),
            accuracy=round(accuracy, 4),
            samples_seen=n_samples * step_epochs,
            parameter_count=self._parameter_count(weights),
            checkpoint_path=saved_path,
        )

    def load_weights(
        self,
        checkpoint_path: Path,
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
    ) -> bool:
        if not checkpoint_path.exists():
            return False

        expected = self._expected_shapes(vocab_size, hidden_dim, num_layers)
        try:
            with np.load(checkpoint_path, allow_pickle=False) as archive:
                loaded: dict[str, np.ndarray] = {}
                for key, shape in expected.items():
                    if key not in archive.files:
                        return False
                    arr = np.asarray(archive[key], dtype=np.float32)
                    if arr.shape != shape:
                        return False
                    loaded[key] = arr
        except Exception:
            return False

        self._weights[(vocab_size, hidden_dim, num_layers)] = loaded
        return True

    def clear_cache(self) -> None:
        self._weights.clear()
