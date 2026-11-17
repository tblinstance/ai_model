"""Requirement-aware code synthesis pipeline supporting Python, TypeScript, SQL, and Bash."""

from __future__ import annotations

import re

from ..models import BaseAIModel, EnsembleInference
from ..schemas import GenerationRequest, ModelTier, TaskType
from .base_pipeline import BasePipeline

LANGUAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "typescript": ("typescript", "react", "tsx", "vue", "axios", "frontend", "interface"),
    "sql": ("sql", "postgres", "sqlite", "query", "select", "table", "billing", "migration"),
    "bash": (
        "bash",
        "shell",
        "makefile",
        "docker",
        "curl",
        "cli",
        "pkill",
        "script",
        "install",
        "setup",
        "venv",
        "pip install",
        "poetry add",
        "npm install",
        "django-admin",
    ),
    "python": (
        "python",
        "numpy",
        "pillow",
        "matplotlib",
        "django",
        "fastapi",
        "pytorch",
        "tensorflow",
        "keras",
        "httpx",
        "pytest",
    ),
}

_INSTALL_CUES: tuple[str, ...] = (
    "install",
    "installation",
    "setup",
    "set up",
    "quickstart",
    "getting started",
    "bootstrap",
    "pip install",
    "poetry add",
    "npm install",
    "virtualenv",
    "venv",
    "startproject",
)

_CODE_STRUCTURE_CUES: tuple[str, ...] = (
    "model",
    "serializer",
    "view",
    "api",
    "endpoint",
    "component",
    "hook",
    "function",
    "class",
    "query",
    "select",
    "table",
    "migration",
    "algorithm",
)

_PACKAGE_EXTRACT_IGNORE: set[str] = {
    "install",
    "installation",
    "setup",
    "set",
    "up",
    "tutorial",
    "guide",
    "quickstart",
    "getting",
    "started",
    "bootstrap",
    "how",
    "to",
    "on",
    "in",
    "for",
    "with",
    "and",
    "ubuntu",
    "linux",
    "python",
    "bash",
    "code",
}


class CodePipeline(BasePipeline):
    """Generates clean, structured, tier-aware code snippets tailored to prompt requirements."""

    task = TaskType.CODE

    @staticmethod
    def _is_install_or_setup_prompt(lowered: str) -> bool:
        if any(cue in lowered for cue in _INSTALL_CUES):
            return True
        return "tutorial" in lowered and not any(cue in lowered for cue in _CODE_STRUCTURE_CUES)

    @classmethod
    def _detect_language(cls, request: GenerationRequest) -> str:
        lowered_prompt = request.prompt.lower()
        explicit = request.language.lower().strip() if request.language else None
        if explicit in {"typescript", "sql", "bash"}:
            return explicit
        if cls._is_install_or_setup_prompt(lowered_prompt) and (explicit is None or explicit == "python"):
            return "bash"
        if explicit:
            return explicit
        combined = " ".join(m.content for m in request.messages[-2:]) + " " + request.prompt
        lowered = combined.lower()
        for lang, keywords in LANGUAGE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return lang
        return "python"

    @staticmethod
    def _install_tutorial_snippet(clean_goal: str, lowered: str, tier: ModelTier, header: str) -> str:
        prefix = f"#!/usr/bin/env bash\n# {header} | Task: {clean_goal}\nset -euo pipefail\n\n"
        if any(k in lowered for k in ("django", "drf", "django-admin")):
            extra_block = ""
            if tier in {ModelTier.PRO, ModelTier.ADVANCE}:
                extra_block = (
                    "\n# 6. Register 'rest_framework' and 'core' in config/settings.py INSTALLED_APPS,\n"
                    "#    then run system checks & start development server:\n"
                    "python manage.py check\n"
                    "python manage.py runserver 127.0.0.1:8000\n"
                )
            else:
                extra_block = "\n# 6. Run Django system check and launch development server\npython manage.py check\npython manage.py runserver 127.0.0.1:8000\n"
            return (
                prefix
                + "# 1. Create and activate an isolated Python virtual environment\n"
                + "python3 -m venv .venv\n"
                + "source .venv/bin/activate\n\n"
                + "# 2. Upgrade pip and install Django + Django REST Framework\n"
                + "python -m pip install --upgrade pip\n"
                + "pip install django djangorestframework\n\n"
                + "# 3. Verify installed Django version\n"
                + "python -m django --version\n\n"
                + "# 4. Scaffold project ('config') and your first app ('core')\n"
                + "django-admin startproject config .\n"
                + "python manage.py startapp core\n\n"
                + "# 5. Apply initial SQLite/PostgreSQL migrations\n"
                + "python manage.py migrate\n"
                + extra_block
            )

        if any(k in lowered for k in ("fastapi", "uvicorn")):
            return (
                prefix
                + "# 1. Create and activate virtual environment\n"
                + "python3 -m venv .venv && source .venv/bin/activate\n\n"
                + "# 2. Install FastAPI and Uvicorn ASGI server\n"
                + "pip install fastapi uvicorn[standard]\n\n"
                + "# 3. Create minimal main.py entrypoint\n"
                + "cat <<'EOF' > main.py\n"
                + "from fastapi import FastAPI\n\n"
                + "app = FastAPI(title='API Service')\n\n"
                + "@app.get('/health')\n"
                + "async def health():\n"
                + "    return {'status': 'ok'}\n"
                + "EOF\n\n"
                + "# 4. Launch reload server (open http://127.0.0.1:8000/docs)\n"
                + "uvicorn main:app --host 127.0.0.1 --port 8000 --reload\n"
            )

        if any(k in lowered for k in ("react", "vite", "next", "typescript", "frontend")):
            return (
                prefix
                + "# 1. Verify Node.js & npm versions\n"
                + "node -v && npm -v\n\n"
                + "# 2. Scaffold React + TypeScript app with Vite\n"
                + "npm create vite@latest my-app -- --template react-ts\n"
                + "cd my-app\n\n"
                + "# 3. Install dependencies and start local dev server\n"
                + "npm install\n"
                + "npm run dev\n"
            )

        if any(k in lowered for k in ("postgres", "postgresql", "psql")):
            return (
                prefix
                + "# 1. Install PostgreSQL server & client tools (Ubuntu/Debian)\n"
                + "sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib\n\n"
                + "# 2. Ensure service is active and create app role/database\n"
                + "sudo systemctl enable --now postgresql\n"
                + "sudo -u postgres createuser --superuser app_user || true\n"
                + "sudo -u postgres createdb -O app_user app_db || true\n\n"
                + "# 3. Verify connectivity\n"
                + "psql -h 127.0.0.1 -U app_user -d app_db -c 'SELECT version();'\n"
            )

        if any(k in lowered for k in ("pytorch", "torch", "tensorflow", "keras", "numpy", "pillow", "matplotlib", "imageio-ffmpeg")):
            pkgs = [
                pkg
                for pkg in ("numpy", "torch", "tensorflow", "keras", "pillow", "matplotlib", "imageio-ffmpeg")
                if pkg in lowered or (pkg == "torch" and "pytorch" in lowered)
            ]
            install_list = " ".join(pkgs or ["numpy", "pillow", "matplotlib"])
            return (
                prefix
                + "# 1. Create and activate virtual environment\n"
                + "python3 -m venv .venv && source .venv/bin/activate\n\n"
                + "# 2. Install AI & media packages\n"
                + f"python -m pip install --upgrade pip\n"
                + f"pip install {install_list}\n\n"
                + "# 3. Verify imports\n"
                + f"python -c \"import importlib; print([(p, getattr(importlib.import_module(p.replace('-', '_')), '__version__', 'ok')) for p in {install_list.split()!r}])\"\n"
            )

        if "docker" in lowered:
            return (
                prefix
                + "# 1. Check Docker Engine and Compose v2\n"
                + "docker --version && docker compose version\n\n"
                + "# 2. Build and start containers in detached mode\n"
                + "docker compose up -d --build\n"
                + "docker compose ps\n"
            )

        tokens = [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", lowered) if t not in _PACKAGE_EXTRACT_IGNORE]
        target_pkg = tokens[0] if tokens else "requests"
        return (
            prefix
            + "# 1. Create and activate an isolated Python virtual environment\n"
            + "python3 -m venv .venv\n"
            + "source .venv/bin/activate\n\n"
            + f"# 2. Install '{target_pkg}' and verify import\n"
            + "python -m pip install --upgrade pip\n"
            + f"pip install {target_pkg}\n"
            + f"python -c \"import {target_pkg.replace('-', '_')}; print('Installed {target_pkg} successfully')\"\n"
        )

    @staticmethod
    def _python_snippet(clean_goal: str, lowered: str, header: str) -> str:
        if any(k in lowered for k in ("pillow", "matplotlib", "image", "video", "gif", "colormap", "pil")):
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"import io\nimport matplotlib\nimport numpy as np\nfrom PIL import Image, ImageEnhance\n\n\n"
                f"def render_spatial_png(height: int = 256, width: int = 256, cmap_name: str = 'plasma') -> bytes:\n"
                f"    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)\n"
                f"    field = 0.5 + 0.5 * np.sin(xx * 0.05) * np.cos(yy * 0.05)\n"
                f"    rgba = matplotlib.colormaps.get_cmap(cmap_name)(field)\n"
                f"    rgb = np.clip(rgba[..., :3] * 255.0, 0, 255).astype(np.uint8)\n"
                f"    img = ImageEnhance.Contrast(Image.fromarray(rgb, mode='RGB')).enhance(1.08)\n"
                f"    buf = io.BytesIO()\n"
                f"    img.save(buf, format='PNG', optimize=True)\n"
                f"    return buf.getvalue()\n"
            )
        if any(k in lowered for k in ("numpy", "vector", "matrix", "cosine", "ndarray")):
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"import numpy as np\n\n\n"
                f"def topk_cosine_similarity(corpus: np.ndarray, query: np.ndarray, k: int = 5) -> np.ndarray:\n"
                f"    corpus_norm = corpus / np.maximum(np.linalg.norm(corpus, axis=1, keepdims=True), 1e-8)\n"
                f"    query_norm = query / np.maximum(np.linalg.norm(query), 1e-8)\n"
                f"    scores = corpus_norm @ query_norm\n"
                f"    top_idx = np.argpartition(scores, -min(k, len(scores)))[-min(k, len(scores)):]\n"
                f"    return top_idx[np.argsort(scores[top_idx])[::-1]]\n"
            )
        if any(k in lowered for k in ("fastapi", "uvicorn", "pydantic", "endpoint", "sse", "stream")):
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"from fastapi import APIRouter\nfrom pydantic import BaseModel, Field\n\n"
                f"router = APIRouter(prefix='/api/v1/tasks', tags=['Tasks'])\n\n\n"
                f"class TaskPayload(BaseModel):\n"
                f"    prompt: str = Field(..., min_length=1, max_length=16000)\n"
                f"    tier: str = Field(default='flash', pattern='^(flash|pro|advance)$')\n\n\n"
                f"@router.post('/run')\n"
                f"async def run_task(payload: TaskPayload) -> dict[str, str]:\n"
                f"    return {{'status': 'ok', 'tier': payload.tier, 'prompt': payload.prompt}}\n"
            )
        if any(k in lowered for k in ("pytorch", "torch", "neural", "train", "transformer")):
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"import torch\nimport torch.nn as nn\n\n\n"
                f"class NeuralClassifier(nn.Module):\n"
                f"    def __init__(self, vocab_size: int = 2048, hidden_dim: int = 128, num_classes: int = 16) -> None:\n"
                f"        super().__init__()\n"
                f"        self.emb = nn.Embedding(vocab_size, hidden_dim, padding_idx=0)\n"
                f"        self.proj = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, num_classes))\n\n"
                f"    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:\n"
                f"        mask = (token_ids != 0).unsqueeze(-1).float()\n"
                f"        pooled = (self.emb(token_ids) * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)\n"
                f"        return self.proj(pooled)\n"
            )
        if any(k in lowered for k in ("django", "drf", "view", "serializer", "orm", "urls")):
            if any(k in lowered for k in ("select_for_update", "atomic", "lock", "quota")):
                return (
                    f'"""{header} | Task: {clean_goal}."""\n\n'
                    f"from django.db import transaction\n\n\n"
                    f"def debit_credits_safely(quota_model, user_id: int, amount: int) -> int:\n"
                    f"    with transaction.atomic():\n"
                    f"        row = quota_model.objects.select_for_update().get(user_id=user_id)\n"
                    f"        if row.balance_credits < amount:\n"
                    f"            raise ValueError('Insufficient credit balance')\n"
                    f"        row.balance_credits -= amount\n"
                    f"        row.save(update_fields=['balance_credits'])\n"
                    f"        return row.balance_credits\n"
                )
            if "serializer" in lowered:
                return (
                    f'"""{header} | Task: {clean_goal}."""\n\n'
                    f"from rest_framework import serializers\n\n\n"
                    f"class PromptRequestSerializer(serializers.Serializer):\n"
                    f"    prompt = serializers.CharField(min_length=1, max_length=16000)\n"
                    f"    tier = serializers.ChoiceField(choices=['flash', 'pro', 'advance'], default='flash')\n\n"
                    f"    def validate_prompt(self, value: str) -> str:\n"
                    f"        cleaned = value.strip()\n"
                    f"        if not cleaned:\n"
                    f"            raise serializers.ValidationError('Prompt cannot be blank.')\n"
                    f"        return cleaned\n"
                )
            if any(k in lowered for k in ("model", "orm", "schema")):
                return (
                    f'"""{header} | Task: {clean_goal}."""\n\n'
                    f"from django.conf import settings\nfrom django.db import models\n\n\n"
                    f"class ProjectItem(models.Model):\n"
                    f"    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')\n"
                    f"    title = models.CharField(max_length=160)\n"
                    f"    body = models.TextField(blank=True, default='')\n"
                    f"    created_at = models.DateTimeField(auto_now_add=True)\n\n"
                    f"    class Meta:\n"
                    f"        ordering = ['-created_at']\n\n"
                    f"    def __str__(self) -> str:\n"
                    f"        return self.title\n"
                )
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"from rest_framework import permissions, status\n"
                f"from rest_framework.request import Request\n"
                f"from rest_framework.response import Response\n"
                f"from rest_framework.views import APIView\n\n\n"
                f"class ProtectedResourceView(APIView):\n"
                f"    permission_classes = [permissions.IsAuthenticated]\n\n"
                f"    def get(self, request: Request) -> Response:\n"
                f'        return Response({{"user": request.user.username, "status": "ok"}}, status=status.HTTP_200_OK)\n'
            )
        if any(k in lowered for k in ("fibonacci", "sort", "algorithm", "prime", "factorial")):
            return (
                f'"""{header} | Task: {clean_goal}."""\n\n'
                f"from functools import lru_cache\n\n\n"
                f"@lru_cache(maxsize=256)\n"
                f"def solve_sequence(n: int) -> int:\n"
                f"    if n < 0:\n"
                f'        raise ValueError("n must be non-negative")\n'
                f"    if n <= 1:\n"
                f"        return n\n"
                f"    return solve_sequence(n - 1) + solve_sequence(n - 2)\n"
            )
        return (
            f'"""{header} | Task: {clean_goal}."""\n\n'
            f"from dataclasses import dataclass\n"
            f"import httpx\n\n\n"
            f"@dataclass(slots=True)\n"
            f"class TaskConfig:\n"
            f'    prompt: str = "{clean_goal}"\n'
            f'    endpoint: str = "http://127.0.0.1:8001/api/v1/chat"\n\n\n'
            f"async def execute_task(cfg: TaskConfig, tier: str = 'pro') -> dict:\n"
            f"    async with httpx.AsyncClient(timeout=30.0) as client:\n"
            f'        response = await client.post(cfg.endpoint, json={{"prompt": cfg.prompt, "tier": tier}})\n'
            f"        response.raise_for_status()\n"
            f"        return response.json()\n"
        )

    @staticmethod
    def _typescript_snippet(clean_goal: str, lowered: str, header: str) -> str:
        if any(k in lowered for k in ("vue", "reactive", "store")):
            return (
                f"// {header} | Task: {clean_goal}\n"
                f"import {{ reactive }} from 'vue';\n\n"
                f"export const workspaceStore = reactive({{\n"
                f"  activeTier: 'flash' as 'flash' | 'pro' | 'advance',\n"
                f"  activeBackend: 'numpy' as 'numpy' | 'pytorch' | 'tensorflow' | 'keras' | 'hybrid',\n"
                f"  formatUsd: (credits: number) => `$${{(credits * 0.01).toFixed(2)}}`,\n"
                f"}});\n"
            )
        if any(k in lowered for k in ("react", "component", "tsx", "hook", "button")):
            return (
                f"// {header} | Task: {clean_goal}\n"
                f"import {{ useState }} from 'react';\n\n"
                f"export function ActionPanel({{ title }}: {{ title: string }}) {{\n"
                f"  const [loading, setLoading] = useState(false);\n"
                f"  return (\n"
                f"    <button type=\"button\" disabled={{loading}} onClick={{() => setLoading(true)}}>\n"
                f"      {{loading ? 'Running...' : title}}\n"
                f"    </button>\n"
                f"  );\n"
                f"}}\n"
            )
        return (
            f"// {header} | Task: {clean_goal}\n"
            f"import axios from 'axios';\n\n"
            f"export interface InferencePayload {{\n"
            f"  prompt: string;\n"
            f"  tier: 'flash' | 'pro' | 'advance';\n"
            f"  conversation_id?: number | null;\n"
            f"}}\n\n"
            f"export async function runModelTask(payload: InferencePayload) {{\n"
            f"  const {{ data }} = await axios.post('/api/v1/generate/chat/', payload);\n"
            f"  return data;\n"
            f"}}\n"
        )

    @staticmethod
    def _sql_snippet(clean_goal: str, lowered: str, header: str) -> str:
        if any(k in lowered for k in ("index", "gin", "jsonb", "migration")):
            return (
                f"-- {header} | Task: {clean_goal}\n"
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_samples_intent\n"
                f"    ON api_trainingsamplerecord (intent, task)\n"
                f"    WHERE is_active = TRUE;\n"
            )
        if any(k in lowered for k in ("for update", "transaction", "wallet", "credit", "mfs", "lock")):
            return (
                f"-- {header} | Task: {clean_goal}\n"
                f"BEGIN;\n"
                f"SELECT id, balance_credits\n"
                f"FROM quota_userquota\n"
                f"WHERE user_id = $1\n"
                f"FOR UPDATE;\n\n"
                f"UPDATE quota_userquota\n"
                f"SET balance_credits = balance_credits - $2\n"
                f"WHERE user_id = $1 AND balance_credits >= $2;\n"
                f"COMMIT;\n"
            )
        if any(k in lowered for k in ("conversation", "message", "chat history", "thread")):
            return (
                f"-- {header} | Task: {clean_goal}\n"
                f"SELECT\n"
                f"    c.id AS conversation_id,\n"
                f"    c.title,\n"
                f"    m.role,\n"
                f"    m.content,\n"
                f"    m.created_at\n"
                f"FROM api_conversation c\n"
                f"JOIN api_conversationmessage m ON m.conversation_id = c.id\n"
                f"WHERE c.user_id = $1\n"
                f"ORDER BY c.updated_at DESC, m.id ASC;\n"
            )
        return (
            f"-- {header} | Task: {clean_goal}\n"
            f"SELECT\n"
            f"    user_id,\n"
            f"    model_tier,\n"
            f"    COUNT(*) AS total_runs,\n"
            f"    SUM(credits_consumed) AS credits_spent\n"
            f"FROM quota_quotausagelog\n"
            f"GROUP BY user_id, model_tier\n"
            f"ORDER BY credits_spent DESC;\n"
        )

    @classmethod
    def _bash_snippet(cls, clean_goal: str, lowered: str, tier: ModelTier, header: str) -> str:
        if cls._is_install_or_setup_prompt(lowered):
            return cls._install_tutorial_snippet(clean_goal, lowered, tier, header)
        if any(k in lowered for k in ("train", "make", "restart", "pkill", "check")):
            return (
                f"#!/usr/bin/env bash\n"
                f"# {header} | Task: {clean_goal}\n"
                f"set -euo pipefail\n\n"
                f"make train\n"
                f"make pkill && make start\n"
                f"curl -fsS -m 5 http://127.0.0.1:8001/api/v1/health\n"
            )
        if any(k in lowered for k in ("postgres", "pg_dump", "pg_ctl", "backup", "database")):
            return (
                f"#!/usr/bin/env bash\n"
                f"# {header} | Task: {clean_goal}\n"
                f"set -euo pipefail\n\n"
                f"pg_isready -h 127.0.0.1 -p 5433\n"
                f"pg_dump -h 127.0.0.1 -p 5433 -U ai_model -Fc -f ai_model_backup.dump ai_model\n"
            )
        return (
            f"#!/usr/bin/env bash\n"
            f"# {header} | Task: {clean_goal}\n"
            f"set -euo pipefail\n\n"
            f"curl -fsS -X POST http://127.0.0.1:8001/api/v1/chat \\\n"
            f"  -H 'Content-Type: application/json' \\\n"
            f"  -d '{{\"prompt\": \"{clean_goal}\", \"tier\": \"{tier.value}\"}}'\n"
        )

    def _synthesize_snippet(
        self,
        language: str,
        prompt: str,
        tier: ModelTier,
        encoding: EnsembleInference,
    ) -> str:
        clean_goal = prompt.strip().replace('"', "'")
        lowered = prompt.lower()
        header = f"Generated by tblinc AI ({tier.value}) | Confidence: {encoding.confidence_score:.2f}"

        if language == "typescript":
            return self._typescript_snippet(clean_goal, lowered, header)
        if language == "sql":
            return self._sql_snippet(clean_goal, lowered, header)
        if language == "bash":
            return self._bash_snippet(clean_goal, lowered, tier, header)
        return self._python_snippet(clean_goal, lowered, header)

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        return "\n" in text and any(
            marker in text
            for marker in (
                "def ",
                "async def ",
                "import ",
                "from ",
                "export ",
                "interface ",
                "const ",
                "SELECT ",
                "CREATE ",
                "INSERT ",
                "UPDATE ",
                "BEGIN;",
                "#!/usr/bin/env",
                "class ",
                "pip install",
                "python -m ",
                "django-admin",
                "npm ",
                "apt-get",
                "docker ",
                "source ",
                "curl ",
            )
        )

    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object]:
        language = self._detect_language(request)
        explicit_lang = request.language.lower().strip() if request.language else None
        intent_filter = (
            f"code_{explicit_lang}"
            if explicit_lang in {"typescript", "sql", "bash"}
            else None
        )
        intent_to_lang = {
            "code_python": "python",
            "code_typescript": "typescript",
            "code_sql": "sql",
            "code_bash": "bash",
        }

        trained_guidance: str | None = None
        if self.trainer is not None:
            sample, score = self.trainer.retrieve_best_match(
                request.prompt,
                task=TaskType.CODE,
                min_score=0.58,
                require_multiline=True,
                intent_filter=intent_filter,
            )
            if sample is not None:
                is_custom = any(
                    s.prompt.strip().lower() == sample.prompt.strip().lower()
                    for s in self.trainer.custom_samples
                )
                if is_custom or (score >= 0.62 and self._looks_like_code(sample.response)):
                    resolved_lang = explicit_lang if explicit_lang in {"typescript", "sql", "bash"} else intent_to_lang.get(sample.intent, language)
                    return {
                        "text": f"Retrieved trained `{resolved_lang}` implementation ({score:.0%} match) via {model.spec.display_name}.",
                        "code": sample.response.rstrip() + "\n",
                        "language": resolved_lang,
                        "extra": {
                            "trained_match": True,
                            "matched_custom_sample": is_custom,
                            "matched_intent": sample.intent,
                            "matched_prompt": sample.prompt,
                            "score": score,
                            "lines": len(sample.response.splitlines()),
                            "conversation_id": request.conversation_id,
                        },
                    }

            guidance_sample, _ = self.trainer.retrieve_best_match(request.prompt, task=TaskType.CODE, min_score=0.65)
            if guidance_sample is not None:
                trained_guidance = guidance_sample.response

        snippet = self._synthesize_snippet(language, request.prompt, model.spec.tier, encoding)
        extra: dict[str, object] = {
            "frameworks_invoked": encoding.frameworks_invoked,
            "lines": len(snippet.splitlines()),
            "conversation_id": request.conversation_id,
        }
        if trained_guidance is not None:
            extra["trained_guidance"] = trained_guidance

        return {
            "text": f"Generated `{language}` implementation using {model.spec.display_name}.",
            "code": snippet,
            "language": language,
            "extra": extra,
        }
