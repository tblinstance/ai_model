"""AI Engine package integrating NumPy, PyTorch, TensorFlow, and Keras across Flash, Pro, and Advance models."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def _configure_runtime_env() -> None:
    """Silence noisy C++/CUDA probe logs on CPU hosts without hiding real GPUs."""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    if "CUDA_VISIBLE_DEVICES" not in os.environ and not Path("/dev/nvidiactl").exists():
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    # Cap CPU BLAS/OpenMP threads to avoid container spinlock contention (up to 7x faster on CPU)
    if not Path("/dev/nvidiactl").exists():
        os.environ.setdefault("OMP_NUM_THREADS", "2")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
        os.environ.setdefault("MKL_NUM_THREADS", "2")
        os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
        os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
    if "MPLCONFIGDIR" not in os.environ:
        mpl_dir = Path.home() / ".config" / "matplotlib"
        if not (mpl_dir.exists() and os.access(mpl_dir, os.W_OK)):
            tmp_mpl = Path(tempfile.gettempdir()) / "matplotlib"
            tmp_mpl.mkdir(parents=True, exist_ok=True)
            os.environ["MPLCONFIGDIR"] = str(tmp_mpl)


_configure_runtime_env()

from .config import EngineSettings, TIER_SPECS
from .exceptions import (
    AIEngineError,
    GenerationError,
    ModelNotFoundError,
    UnsupportedBackendError,
)
from .registry import ModelRegistry
from .router import AIEngineRouter
from .schemas import (
    AllTiersTrainingResult,
    BackendTrainingStats,
    ChatMessage,
    CheckpointInfo,
    EvaluationRequest,
    EvaluationResult,
    FrameworkBackend,
    GenerationRequest,
    GenerationResponse,
    ModelSummary,
    ModelTier,
    NeuralDiagnostics,
    TaskType,
    TierSpec,
    TrainingRequest,
    TrainingResult,
    TrainingSample,
    TrainingStatusResponse,
)

__all__ = [
    "AIEngineError",
    "AIEngineRouter",
    "AllTiersTrainingResult",
    "BackendTrainingStats",
    "ChatMessage",
    "CheckpointInfo",
    "EngineSettings",
    "EvaluationRequest",
    "EvaluationResult",
    "FrameworkBackend",
    "GenerationError",
    "GenerationRequest",
    "GenerationResponse",
    "ModelNotFoundError",
    "ModelRegistry",
    "ModelSummary",
    "ModelTier",
    "NeuralDiagnostics",
    "TIER_SPECS",
    "TaskType",
    "TierSpec",
    "TrainingRequest",
    "TrainingResult",
    "TrainingSample",
    "TrainingStatusResponse",
    "UnsupportedBackendError",
]

