"""PyTorch neural backend providing transformer encoding and spatial synthesis."""

from __future__ import annotations

import math
import os
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

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]


class _PyTorchTransformerEncoder(nn.Module):  # type: ignore[misc]
    """Compact PyTorch transformer block for token representation and pooling."""

    def __init__(self, vocab_size: int, hidden_dim: int, num_layers: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_dim, padding_idx=0)
        nhead = max(1, min(8, hidden_dim // 16))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=nhead,
            dim_feedforward=hidden_dim * 2,
            dropout=0.0,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=max(1, num_layers),
            enable_nested_tensor=False,
        )
        self.head = nn.Linear(hidden_dim, 16)

    def forward(self, input_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        embedded = self.embedding(input_ids)
        encoded = self.encoder(embedded)
        mask = (input_ids != 0).unsqueeze(-1).float()
        denom = mask.sum(dim=1).clamp(min=1.0)
        pooled = (encoded * mask).sum(dim=1) / denom
        logits = self.head(pooled)
        return pooled, logits


class PyTorchBackend(BaseNeuralBackend):
    """PyTorch execution backend supporting CPU and CUDA devices."""

    name = "pytorch"

    def __init__(self, device_preference: str = "auto") -> None:
        self.device_preference = device_preference
        self._model_cache: dict[tuple[int, int, int], _PyTorchTransformerEncoder] = {}
        if torch is not None and not torch.cuda.is_available():
            try:
                torch.set_num_threads(min(2, max(1, os.cpu_count() or 2)))
            except Exception:
                pass

    def _resolve_device(self) -> str:
        if torch is None:
            return "unavailable"
        if self.device_preference == "cpu":
            return "cpu"
        if self.device_preference == "cuda" and torch.cuda.is_available():
            return "cuda"
        return "cuda" if torch.cuda.is_available() else "cpu"

    def health(self) -> BackendHealth:
        if torch is None:
            return BackendHealth(name=self.name, available=False, version="not-installed", device="none")
        device = self._resolve_device()
        return BackendHealth(
            name=self.name,
            available=True,
            version=torch.__version__,
            device=device,
            details={
                "cuda_available": bool(torch.cuda.is_available()),
                "device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
            },
        )

    def _get_model(self, vocab_size: int, hidden_dim: int, num_layers: int, device: str) -> _PyTorchTransformerEncoder:
        key = (vocab_size, hidden_dim, num_layers)
        if key not in self._model_cache:
            torch.manual_seed(42 + hidden_dim + num_layers)
            model = _PyTorchTransformerEncoder(vocab_size, hidden_dim, num_layers).to(device)
            model.eval()
            self._model_cache[key] = model
        return self._model_cache[key]

    def encode_tokens(
        self,
        token_ids: list[int],
        hidden_dim: int,
        num_layers: int,
        vocab_size: int = 2048,
        seed: int | None = None,
    ) -> BackendResult:
        if torch is None:
            raise RuntimeError("PyTorch is not installed.")
        device = self._resolve_device()
        model = self._get_model(vocab_size, hidden_dim, num_layers, device)
        if seed is not None:
            torch.manual_seed(seed)

        safe_ids = [max(0, min(vocab_size - 1, tid)) for tid in token_ids] or [1]
        tensor_in = torch.tensor([safe_ids], dtype=torch.long, device=device)
        with torch.no_grad():
            pooled, logits = model(tensor_in)
            norm = float(torch.linalg.vector_norm(pooled).item())
            probs = torch.softmax(logits, dim=-1)
            confidence = float(torch.max(probs).item())

        param_count = sum(p.numel() for p in model.parameters())
        latent_vec = [round(float(v), 5) for v in logits.squeeze(0).cpu().tolist()]
        confidence = round(min(0.99, max(0.55, 0.55 + confidence * 2.2)), 4)
        return BackendResult(
            backend=self.name,
            device=device,
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
        if torch is None:
            raise RuntimeError("PyTorch is not installed.")
        device = self._resolve_device()
        seed_val = seed if seed is not None else (sum(token_ids) % 100000)
        generator = torch.Generator(device=device).manual_seed(seed_val)

        # Generate low-res latent grid and bicubic-upsample via PyTorch neural conv filter
        latent_h, latent_w = max(8, height // 16), max(8, width // 16)
        latent = torch.randn((1, 8, latent_h, latent_w), generator=generator, device=device)

        # Condition channels with token harmonics
        token_phase = torch.tensor(
            [math.sin((tid % 97) * 0.13 + i * 0.7) for i, tid in enumerate((token_ids * 8)[:8])],
            device=device,
        ).view(1, 8, 1, 1)
        conditioned = torch.tanh(latent + token_phase * 0.85)

        with torch.no_grad():
            conv = nn.Conv2d(8, channels, kernel_size=3, padding=1, device=device)
            torch.manual_seed(seed_val)
            nn.init.xavier_uniform_(conv.weight)
            projected = conv(conditioned)
            upsampled = torch.nn.functional.interpolate(
                projected,
                size=(height, width),
                mode="bicubic",
                align_corners=False,
            )
            # Add smooth radial/wave coordinate field for coherent composition
            yy = torch.linspace(-1.0, 1.0, height, device=device).view(1, 1, height, 1)
            xx = torch.linspace(-1.0, 1.0, width, device=device).view(1, 1, 1, width)
            freq = 1.5 + (seed_val % 5) * 0.45
            wave = torch.sin(xx * freq + yy * (freq * 0.7)) * 0.35
            combined = torch.sigmoid(upsampled + wave)
            array = combined.squeeze(0).permute(1, 2, 0).clamp(0.0, 1.0).cpu().numpy()
        return array.astype(np.float32)

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
        if torch is None:
            raise RuntimeError("PyTorch is not installed.")
        device = self._resolve_device()
        cached_model = self._get_model(vocab_size, hidden_dim, num_layers, device)
        model = _PyTorchTransformerEncoder(vocab_size, hidden_dim, num_layers).to(device)
        model.load_state_dict({k: v.clone() for k, v in cached_model.state_dict().items()})
        x_np, y_np = prepare_training_batch(examples, seq_len=32, vocab_size=vocab_size)
        nz_cols = np.flatnonzero(x_np.any(axis=0))
        active_len = max(8, int(nz_cols[-1]) + 1) if len(nz_cols) > 0 else 8
        x_np = x_np[:, :active_len]
        x_t = torch.from_numpy(x_np).to(device=device, dtype=torch.long)
        y_t = torch.from_numpy(y_np).to(device=device, dtype=torch.long)

        def _eval_loss_acc() -> tuple[float, float]:
            eval_bs = 256
            total_loss = 0.0
            correct = 0
            model.eval()
            with torch.no_grad():
                for start in range(0, len(examples), eval_bs):
                    bx = x_t[start : start + eval_bs]
                    by = y_t[start : start + eval_bs]
                    _, logits = model(bx)
                    total_loss += float(criterion(logits, by).item()) * len(bx)
                    correct += int((torch.argmax(logits, dim=-1) == by).sum().item())
            return total_loss / max(1, len(examples)), correct / max(1, len(examples))

        criterion = nn.CrossEntropyLoss()
        initial_loss, _ = _eval_loss_acc()

        if not math.isfinite(initial_loss) or initial_loss > 25.0:
            self._model_cache.pop((vocab_size, hidden_dim, num_layers), None)
            model = self._get_model(vocab_size, hidden_dim, num_layers, device)
            initial_loss, _ = _eval_loss_acc()

        model.train()
        opt_lr = effective_learning_rate(learning_rate, hidden_dim, num_layers, backend_scale=0.35)
        optimizer = torch.optim.AdamW(model.parameters(), lr=opt_lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs))
        batch_size = adaptive_batch_size(len(examples))
        for _ in range(epochs):
            perm = torch.randperm(len(examples), device=device)
            for start in range(0, len(examples), batch_size):
                idx = perm[start : start + batch_size]
                bx = x_t[idx]
                row_nz = (bx != 0).any(dim=0).nonzero(as_tuple=False)
                if len(row_nz) > 0:
                    bx = bx[:, : int(row_nz[-1].item()) + 1]
                optimizer.zero_grad()
                _, logits = model(bx)
                loss = criterion(logits, y_t[idx])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.5)
                optimizer.step()
            scheduler.step()

        final_loss, accuracy = _eval_loss_acc()
        model.eval()
        self._model_cache[(vocab_size, hidden_dim, num_layers)] = model

        saved_path: str | None = None
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), checkpoint_path)
            saved_path = str(checkpoint_path)

        param_count = sum(p.numel() for p in model.parameters())
        return BackendTrainingOutcome(
            backend=self.name,
            device=device,
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
        if torch is None or not checkpoint_path.exists():
            return False
        device = self._resolve_device()
        model = _PyTorchTransformerEncoder(vocab_size, hidden_dim, num_layers).to(device)
        try:
            state = torch.load(checkpoint_path, map_location=device, weights_only=True)
            model.load_state_dict(state)
        except Exception:
            return False
        model.eval()
        self._model_cache[(vocab_size, hidden_dim, num_layers)] = model
        return True

    def clear_cache(self) -> None:
        self._model_cache.clear()

