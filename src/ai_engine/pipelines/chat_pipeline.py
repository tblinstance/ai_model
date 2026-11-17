"""Conversational multi-turn chat generation pipeline across Flash, Pro, and Advance tiers."""

from __future__ import annotations

import ast
from collections.abc import Iterator
import math
import operator
import re
from typing import Any

from ..models import BaseAIModel, EnsembleInference
from ..schemas import ChatMessage, GenerationRequest, ModelTier, TaskType
from .base_pipeline import BasePipeline
from .media_renderer import decode_reference_frames, decode_reference_image

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MATH_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

_MATH_FUNCS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
}

_NON_NAME_WORDS = {
    "a",
    "an",
    "ai",
    "asking",
    "fine",
    "good",
    "great",
    "here",
    "just",
    "looking",
    "new",
    "not",
    "ok",
    "okay",
    "ready",
    "sure",
    "testing",
    "trying",
    "working",
}


class ChatPipeline(BasePipeline):
    """Generates accurate, context-aware, tier-scaled responses grounded in neural intents."""

    task = TaskType.CHAT

    def __init__(
        self,
        storage,
        tokenizer,
        trainer=None,
        images_pipeline: BasePipeline | None = None,
        video_pipeline: BasePipeline | None = None,
    ) -> None:
        super().__init__(storage, tokenizer, trainer=trainer)
        self.images_pipeline = images_pipeline
        self.video_pipeline = video_pipeline

    @staticmethod
    def _eval_math_ast(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return ChatPipeline._eval_math_ast(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("Unsupported literal")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in _MATH_CONSTANTS:
                return _MATH_CONSTANTS[node.id]
            raise ValueError("Unknown constant")
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return float(_UNARY_OPS[type(node.op)](ChatPipeline._eval_math_ast(node.operand)))
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left = ChatPipeline._eval_math_ast(node.left)
            right = ChatPipeline._eval_math_ast(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 500:
                raise ValueError("Exponent out of range")
            return float(_BIN_OPS[type(node.op)](left, right))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _MATH_FUNCS:
            if node.keywords or len(node.args) > 2:
                raise ValueError("Unsupported call signature")
            args = [ChatPipeline._eval_math_ast(arg) for arg in node.args]
            return float(_MATH_FUNCS[node.func.id](*args))
        raise ValueError("Unsupported expression")

    @classmethod
    def _try_solve_math(cls, prompt: str) -> tuple[str, str] | None:
        normalized = prompt.strip()
        normalized = normalized.replace("×", "*").replace("÷", "/").replace("^", "**")
        normalized = re.sub(
            r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)",
            r"((\1 / 100) * \2)",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"(\d),(\d{3})", r"\1\2", normalized)

        pattern = re.compile(
            r"(?:\(\s*)*(?:(?:sqrt|abs|round|sin|cos|tan|log10|log|exp|pow)\s*\([^()]+\)|\b(?:pi|e|tau)\b|\d+(?:\.\d+)?)"
            r"(?:[\s()+\-*/%]+(?:(?:sqrt|abs|round|sin|cos|tan|log10|log|exp|pow)\s*\([^()]+\)|\b(?:pi|e|tau)\b|\d+(?:\.\d+)?|\)))*(?:\s*\))*"
        )
        matches = [m.group(0).strip() for m in pattern.finditer(normalized)]
        candidates = sorted(
            (c for c in matches if any(op in c for op in "+-*/%") or re.search(r"\b(?:sqrt|abs|round|sin|cos|tan|log10|log|exp|pow)\s*\(", c)),
            key=len,
            reverse=True,
        )
        for expr in candidates:
            clean = expr.rstrip("?.!,:; ")
            if not clean:
                continue
            try:
                tree = ast.parse(clean, mode="eval")
                value = cls._eval_math_ast(tree)
                if not math.isfinite(value):
                    continue
                formatted = str(int(round(value))) if abs(value - round(value)) < 1e-9 else f"{value:.6f}".rstrip("0").rstrip(".")
                return clean, formatted
            except Exception:
                continue
        return None

    @staticmethod
    def _extract_memory(messages: list[ChatMessage]) -> dict[str, Any]:
        user_turns: list[str] = []
        assistant_turns: list[str] = []
        user_name: str | None = None

        for msg in messages:
            text = msg.content.strip()
            if not text:
                continue
            if msg.role == "user":
                user_turns.append(text)
                name_match = re.search(
                    r"\b(?:my name is|call me|i am|i'm)\s+([A-Za-z][A-Za-z0-9_-]{1,24})\b",
                    text,
                    flags=re.IGNORECASE,
                )
                if name_match:
                    candidate = name_match.group(1)
                    if candidate.lower() not in _NON_NAME_WORDS:
                        user_name = candidate
            elif msg.role == "assistant":
                assistant_turns.append(text)

        return {
            "user_name": user_name,
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "turn_count": len(user_turns) + len(assistant_turns),
        }

    @staticmethod
    def _handle_memory_query(prompt: str, memory: dict[str, Any], tier: ModelTier) -> str | None:
        lowered = prompt.strip().lower()
        user_turns: list[str] = memory["user_turns"]
        assistant_turns: list[str] = memory["assistant_turns"]
        user_name: str | None = memory["user_name"]

        if any(phrase in lowered for phrase in ("what is my name", "what's my name", "who am i")):
            if user_name:
                return f"You told me earlier that your name is **{user_name}**."
            return "You haven't shared your name in this conversation yet. Tell me your name and I'll remember it across turns."

        if any(phrase in lowered for phrase in ("what did i ask", "earlier question", "previous question", "summarize our", "summarize this conversation", "recap")):
            if not user_turns:
                return "This is the beginning of our conversation — there are no earlier messages yet."
            bullet_lines = "\n".join(f"- Turn {idx + 1}: *\"{turn[:140]}\"*" for idx, turn in enumerate(user_turns[-5:]))
            return (
                f"Here is a summary of your recent conversation turns ({len(user_turns)} user messages):\n\n"
                f"{bullet_lines}\n\n"
                f"Ask a follow-up on any item above and I will expand on it."
            )

        follow_up_cues = ("explain that", "more simply", "simpler", "shorter", "elaborate", "example of that", "continue")
        if user_turns and any(cue in lowered for cue in follow_up_cues):
            prev_q = user_turns[-1][:120]
            prev_a = (assistant_turns[-1][:240] + "...") if assistant_turns else "the previous topic"
            if tier == ModelTier.FLASH:
                return (
                    f"Following up concisely on *\"{prev_q}\"*:\n\n"
                    f"In short: focus on one concrete step at a time—validate inputs cleanly, "
                    f"keep state isolated from compute, and verify outputs with automated checks."
                )
            return (
                f"Expanding on your earlier topic (*\"{prev_q}\"*):\n\n"
                f"Previous context covered: {prev_a}\n\n"
                f"**Practical Example**:\n"
                f"1. Define explicit request/response validation at the API boundary.\n"
                f"2. Persist user state (such as conversation history and quota) inside PostgreSQL before/after compute.\n"
                f"3. Run lightweight targeted verification tests after each refinement."
            )
        return None

    def _detect_domain_intent(self, prompt: str, latent_vector: list[float]) -> str:
        lowered = prompt.lower()
        keyword_rules: list[tuple[str, tuple[str, ...]]] = [
            (
                "greeting",
                (
                    "hello",
                    "hi ",
                    "hey ",
                    "good morning",
                    "good afternoon",
                    "good evening",
                    "how are you",
                    "how r u",
                    "how are u",
                    "how's it going",
                    "how do you do",
                    "who are you",
                    "what can you do",
                    "thank you",
                    "thanks",
                ),
            ),
            ("debugging", ("error", "bug", "traceback", "exception", "failed", "401", "403", "404", "500", "cors", "disallowedhost", "refused", "fix ")),
            ("training_ml", ("train", "training", "epoch", "loss", "weights", "checkpoint", "fine-tune", "finetune")),
            ("billing_quota", ("credit", "quota", "billing", "subscription", "plan", "price", "cost")),
            ("comparison", (" vs ", "versus", "compare", "difference between")),
            ("architecture", ("design", "architecture", "queue", "scalable", "pipeline", "microservice", "gateway", "system")),
            ("image_generation", ("draw", "image", "picture", "illustration", "render", "poster")),
            ("video_generation", ("video", "animation", "gif", "motion", "clip", "frames")),
            ("explanation", ("explain", "how does", "what is", "why does", "concept")),
        ]
        for intent, cues in keyword_rules:
            if any(cue in lowered for cue in cues) or (intent == "greeting" and lowered.strip() in {"hi", "hello", "hey", "thanks", "ty"}):
                return intent

        if self.trainer is not None:
            predicted, conf = self.trainer.predict_intent(latent_vector, prompt)
            if conf >= 0.3:
                return predicted
        return "general"

    def _build_domain_body(
        self,
        intent: str,
        prompt: str,
        model: BaseAIModel,
        encoding: EnsembleInference,
        memory: dict[str, Any],
    ) -> str:
        tier = model.spec.tier
        lowered_prompt = prompt.strip().lower()
        framework_labels = {
            "numpy": "tblinc Cloud Core",
            "pytorch": "tblinc Cloud Flash Engine",
            "tensorflow": "tblinc Cloud Pro Engine",
            "keras": "tblinc Cloud Advance Engine",
        }
        frameworks = ", ".join(
            framework_labels.get(fw, fw.capitalize())
            for fw in encoding.frameworks_invoked
        )
        name_prefix = f"Hi **{memory['user_name']}** — " if memory.get("user_name") else ""

        if intent == "greeting":
            if any(q in lowered_prompt for q in ("how are you", "how r u", "how are u", "how's it going", "how do you do")):
                return (
                    f"{name_prefix}Doing great, thanks for asking! I'm **{model.spec.display_name}** (`tblinc AI`).\n\n"
                    f"How can I help you today? Feel free to ask a question, solve math, write code, or create images and videos."
                )
            if any(t in lowered_prompt for t in ("thank you", "thanks")) or lowered_prompt == "ty":
                return (
                    f"{name_prefix}You're welcome! Let me know whenever you'd like to continue or explore another task."
                )
            return (
                f"{name_prefix}Hello! I'm **{model.spec.display_name}** (`tblinc AI`).\n\n"
                f"I keep multi-turn conversation context in this thread and can help with:\n"
                f"- **Chat & Q&A**: Technical troubleshooting, explanations, planning, and structured writing\n"
                f"- **Code Synthesis**: Switch to **Code** mode or ask for Python, TypeScript, SQL, or Bash\n"
                f"- **Exact Math**: Instant verified calculations and numeric breakdowns\n"
                f"- **Images & Video**: Generate visual previews and animated clips in **Images** or **Video** mode"
            )

        if intent == "debugging":
            return (
                f"**Troubleshooting Triage ({model.spec.display_name})**\n\n"
                f"For *\"{prompt}\"*, check these high-probability root causes in order:\n"
                f"1. **Auth & Hosts (`401` / `400` DisallowedHost)**: Confirm `Authorization: Bearer <jwt>` is attached and allowed origins/hosts are configured.\n"
                f"2. **Cloud Storage & Schema State**: Verify database connectivity and check pending schema migrations.\n"
                f"3. **API Gateway & CORS**: Inspect cloud inference service health and routing configuration."
            )

        if intent == "billing_quota":
            return (
                f"**tblinc AI Tier & Credit Schedule**\n\n"
                f"- **Starter Default**: New users receive `250` starter credits.\n"
                f"- **tblinc Flash**: `1` chat · `2` code · `4` images · `8` video credit(s) per run.\n"
                f"- **tblinc Pro**: `3` chat · `5` code · `10` images · `20` video credits per run.\n"
                f"- **tblinc Advance**: `6` chat · `10` code · `18` images · `36` video credits per run."
            )

        if intent == "training_ml":
            trained_note = ""
            if self.trainer and self.trainer.last_training:
                lt = self.trainer.last_training
                trained_note = (
                    f"\n- **Latest Checkpoint**: `{lt.training_id[:8]}` on `{lt.tier.value}` "
                    f"({lt.dataset_size} samples across {len(lt.backends_trained)} cloud engine(s))."
                )
            return (
                f"**tblinc Cloud Neural Training Pipeline**\n\n"
                f"The platform runs supervised cloud gradient optimization across tblinc Cloud Core, Flash, Pro, and Advance engines, saving versioned Cloud Checkpoints.{trained_note}"
            )

        if intent == "comparison":
            return (
                f"**Structured Comparison ({model.spec.display_name})**\n\n"
                f"Evaluating *\"{prompt}\"* across tblinc AI engines:\n"
                f"- **tblinc Cloud Core**: Zero-overhead vectorized cloud compute for sub-millisecond inference and fast checkpoints.\n"
                f"- **tblinc Cloud Flash Engine**: Responsive deep attention architecture for low-latency reasoning and clean code drafts.\n"
                f"- **tblinc Cloud Pro Engine**: Balanced residual graph engine optimized for complex reasoning and deterministic cloud placement.\n"
                f"- **tblinc Cloud Advance Engine**: Multi-stage cloud synthesis engine delivering studio-grade outputs."
            )

        if intent in {"image_generation", "video_generation"}:
            modality = "Images" if intent == "image_generation" else "Video"
            return (
                f"For **{modality}** synthesis of *\"{prompt}\"*, open **{modality}** from the left sidenav (`{modality}` link) "
                f"to render real tensor-synthesized PNG/WebP images or 10+ minute H.264 MP4 videos directly in your workspace."
            )

        if tier == ModelTier.ADVANCE:
            prior_ctx = f"\n- **Conversation Context**: Incorporating `{len(memory['user_turns'])}` prior user turn(s) from this session." if memory["user_turns"] else ""
            return (
                f"### {model.spec.display_name} — Cloud Ensemble Analysis\n"
                f"*Engines: {frameworks} · Confidence: {encoding.confidence_score:.2f} · Latent Norm: {encoding.latent_norm:.3f}*{prior_ctx}\n\n"
                f"1. **Objective Decomposition**: *\"{prompt}\"* requires separating stateless compute cleanly from persistent state.\n"
                f"2. **Execution Blueprint**: Enforce typed schemas at every gateway boundary, track deterministic diagnostics per run, and persist conversation turns atomically.\n"
                f"3. **Verification**: Validate API contracts through automated integration and end-to-end verification suites."
            )

        if tier == ModelTier.PRO:
            prior_ctx = f"\n- **Thread History**: Aware of `{len(memory['user_turns'])}` earlier turn(s)." if memory["user_turns"] else ""
            return (
                f"### {model.spec.display_name} Response\n"
                f"*Engines: {frameworks} · Confidence: {encoding.confidence_score:.2f}*{prior_ctx}\n\n"
                f"**Core Analysis for *\"{prompt}\"*:**\n"
                f"- Validate input structure at API schemas before dispatching compute.\n"
                f"- Keep transactional records (auth, quota, conversations) isolated in cloud storage while inference runs statelessly.\n"
                f"- Tune tier selection (`flash` for rapid iteration, `pro` for balanced engineering, `advance` for multi-stage synthesis)."
            )

        context_line = f" (continuing a {len(memory['user_turns']) + 1}-turn conversation)" if memory["user_turns"] else ""
        return (
            f"**{model.spec.display_name}** ({frameworks}{context_line}):\n\n"
            f"Regarding *\"{prompt}\"*:\n"
            f"- Structure the workflow into clear input validation, stateless processing, and verified persistence.\n"
            f"- Use follow-up questions in this thread to drill into specific code, architecture steps, or math checks."
        )

    def _build_reply(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> tuple[str, str]:
        prompt = request.prompt.strip()
        memory = self._extract_memory(request.messages)
        sys_ctx = f"*System context: `{request.system_prompt.strip()}`*\n\n" if request.system_prompt else ""

        memory_reply = self._handle_memory_query(prompt, memory, model.spec.tier)
        if memory_reply is not None:
            return f"{sys_ctx}{memory_reply}", "conversation_memory"

        math_result = self._try_solve_math(prompt)
        if math_result is not None:
            expr, value = math_result
            reply = (
                f"{sys_ctx}**Calculated Result ({model.spec.display_name})**\n\n"
                f"- **Expression**: `{expr}`\n"
                f"- **Exact Value**: **`{value}`**"
            )
            return reply, "math_compute"

        if self.trainer is not None:
            sample, score = self.trainer.retrieve_best_match(prompt, task=TaskType.CHAT, min_score=0.45)
            is_custom = sample is not None and any(
                s.prompt.strip().lower() == sample.prompt.strip().lower()
                for s in self.trainer.custom_samples
            )
            if sample is not None and (is_custom or (score >= 0.72 and sample.intent != "greeting")):
                source_tag = "Trained Custom Knowledge" if is_custom else "Trained Domain Knowledge"
                reply = (
                    f"{sys_ctx}**[{model.spec.display_name} · {source_tag} ({score:.0%} match)]**\n\n"
                    f"{sample.response}"
                )
                return reply, sample.intent

        intent = self._detect_domain_intent(prompt, encoding.latent_vector)
        body = self._build_domain_body(intent, prompt, model, encoding, memory)
        return f"{sys_ctx}{body}", intent

    def _handle_uploaded_media(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object] | None:
        meta = request.metadata or {}
        frames_raw = meta.get("reference_frames_base64")
        has_frames = isinstance(frames_raw, list) and len(frames_raw) > 0
        single_raw = meta.get("reference_image_base64")
        if not has_frames and not single_raw:
            return None

        lowered = request.prompt.lower()
        inspect_only = any(
            cue in lowered for cue in ("describe", "analyze", "inspect", "what is", "color", "palette", "dimension", "size")
        ) and not any(
            gen in lowered for gen in ("generate", "create", "render", "draw", "animate", "restyle", "remix", "transform", "video", "gif", "image", "turn", "make")
        )

        if inspect_only:
            frames, info_list = decode_reference_frames(
                frames_raw if has_frames else None,
                str(single_raw) if single_raw else None,
                width=256,
                height=256,
            )
            if not info_list and single_raw:
                dec = decode_reference_image(str(single_raw), target_size=(256, 256))
                if dec is not None:
                    info_list = [dec[1]]
            info = info_list[0] if info_list else {}
            filename = str(meta.get("media_filename") or "uploaded media")
            kind = str(meta.get("media_kind") or ("video" if len(frames) > 1 or has_frames else "image"))
            dims = f"{info.get('orig_width', '?')}x{info.get('orig_height', '?')}"
            summary = (
                f"**Visual Analysis ({model.spec.display_name})**\n\n"
                f"- **Uploaded {kind.title()}**: `{filename}` (`{dims}`, `{info.get('source_format', 'RGB')}`, `{max(1, len(frames))}` sampled frame(s))\n"
                f"- **Color & Brightness**: Dominant mean swatch `{info.get('dominant_hex', '#808080')}` · mean brightness `{info.get('brightness', 0.5):.3f}`\n"
                f"- **Next Step**: Ask `'generate this'` or `'animate this'` to synthesize a styled PNG/WebP or 10+ minute H.264 MP4 video directly from this upload."
            )
            return {
                "text": summary,
                "extra": {
                    "intent": "media_analysis",
                    "reference_info": info,
                    "uploaded_keyframes": len(frames),
                },
            }

        want_video = (
            any(cue in lowered for cue in ("video", "mp4", "animate", "animation", "gif", "motion", "clip", "loop"))
            or (
                (meta.get("media_kind") == "video" or (has_frames and len(frames_raw) > 1))
                and not any(cue in lowered for cue in ("image", "png", "webp", "jpg", "jpeg", "poster", "picture"))
            )
        )
        if want_video and self.video_pipeline is not None:
            result = self.video_pipeline._execute(model, request, encoding)
            extra = dict(result.get("extra") or {})
            extra["intent"] = "video_generation"
            result["extra"] = extra
            return result
        if self.images_pipeline is not None:
            result = self.images_pipeline._execute(model, request, encoding)
            extra = dict(result.get("extra") or {})
            extra["intent"] = "image_generation"
            result["extra"] = extra
            return result
        return None

    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object]:
        media_result = self._handle_uploaded_media(model, request, encoding)
        if media_result is not None:
            return media_result
        reply, intent = self._build_reply(model, request, encoding)
        return {
            "text": reply,
            "extra": {
                "intent": intent,
                "history_turns": len(request.messages),
                "conversation_id": request.conversation_id,
                "latent_preview": encoding.latent_vector[:6],
                "temperature": request.temperature,
            },
        }

    def stream_tokens(self, model: BaseAIModel, request: GenerationRequest) -> Iterator[str]:
        """Yield incremental whitespace-delimited chunks for SSE streaming responses."""
        response = self.run(model, request)
        text = response.text or ""
        words = text.split(" ")
        for idx, word in enumerate(words):
            suffix = " " if idx < len(words) - 1 else ""
            yield word + suffix
