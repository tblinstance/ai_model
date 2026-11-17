"""Django gateway views, persistent conversation CRUD, Vue portal, and FastAPI proxy."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from Agent.models import AgentRun
from billing.serializers import SubscriptionSerializer
from billing.services import get_or_create_subscription
from quota.models import QuotaUsageLog
from quota.serializers import UserQuotaSerializer
from quota.services import (
    InsufficientQuotaError,
    check_user_quota,
    consume_user_quota,
    estimate_request_cost,
    get_or_create_quota,
)
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer
from .fastapi_bridge import FastAPIBridge, FastAPIBridgeError
from .verification import verify_user_account_state
from .models import (
    Conversation,
    ConversationMessage,
    SecretKey,
    TrainingRun,
    TrainingSampleRecord,
    UserProfile,
)
from .serializers import (
    ConversationDetailSerializer,
    ConversationSummarySerializer,
    ConversationWriteSerializer,
    GatewayGenerateSerializer,
    GatewayTrainEvaluateSerializer,
    GatewayTrainSerializer,
    SecretKeyCreateSerializer,
    SecretKeySerializer,
    TrainingRunSerializer,
    TrainingSampleRecordSerializer,
    UserProfileSerializer,
)

TASK_FASTAPI_ENDPOINTS: dict[str, str] = {
    "chat": "/api/v1/chat",
    "images": "/api/v1/images/generate",
    "video": "/api/v1/video/generate",
    "code": "/api/v1/code/generate",
    "audio": "/api/v1/audio/generate",
    "rag": "/api/v1/rag/query",
}


def _auto_title(prompt: str) -> str:
    clean = " ".join(prompt.strip().split())
    if len(clean) <= 56:
        return clean or "New Conversation"
    return clean[:53].rstrip() + "..."


def _user_conversation_or_404(user, pk: int) -> Conversation:
    return get_object_or_404(
        Conversation.objects.prefetch_related("messages"),
        pk=pk,
        user=user,
    )


PORTAL_SECTIONS = {"auth", "overview", "studio", "training", "settings", "admin"}
PORTAL_AUTH_MODES = {"login", "register"}
PORTAL_TASKS = {"chat", "images", "video", "code"}
PORTAL_ADMIN_TABS = {"mfs", "users", "invoices", "transactions"}
PORTAL_SETTINGS_TABS = {
    "general",
    "keys",
    "agents",
    "billing",
    "profiles",
    "transactions",
    "all",
}


def resolve_portal_route(kwargs: dict[str, object], query_params: dict[str, str]) -> dict[str, str]:
    """Resolve and validate initial portal section, auth mode, task mode, admin tab, and settings tab."""
    raw_section = kwargs.get("section") or query_params.get("section") or "overview"
    section = str(raw_section).strip().lower()
    if section not in PORTAL_SECTIONS:
        if "section" in kwargs:
            raise Http404(f"Unknown portal section '{section}'.")
        section = "overview"

    raw_task = kwargs.get("task") or query_params.get("task") or "chat"
    task = str(raw_task).strip().lower()
    if task not in PORTAL_TASKS:
        if "task" in kwargs:
            raise Http404(f"Unknown studio mode '{task}'.")
        task = "chat"

    raw_tab = kwargs.get("tab") or query_params.get("tab") or "general"
    settings_tab = str(raw_tab).strip().lower()
    if settings_tab not in PORTAL_SETTINGS_TABS:
        if "tab" in kwargs:
            raise Http404(f"Unknown settings tab '{settings_tab}'.")
        settings_tab = "general"

    raw_admin_tab = kwargs.get("admin_tab") or query_params.get("admin_tab") or "mfs"
    admin_tab = str(raw_admin_tab).strip().lower()
    if admin_tab not in PORTAL_ADMIN_TABS:
        if "admin_tab" in kwargs:
            raise Http404(f"Unknown admin tab '{admin_tab}'.")
        admin_tab = "mfs"

    route = {
        "section": section,
        "task": task,
        "settingsTab": settings_tab,
        "adminTab": admin_tab,
    }
    if section == "auth":
        raw_mode = kwargs.get("mode") or query_params.get("mode") or "login"
        mode = str(raw_mode).strip().lower()
        route["mode"] = mode if mode in PORTAL_AUTH_MODES else "login"
    return route


class PortalHomeView(TemplateView):
    """Serves the Vue 3 CDN interactive AI Studio & Billing portal."""

    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fastapi_base_url"] = settings.FASTAPI_BASE_URL
        context["portal_route"] = resolve_portal_route(self.kwargs, self.request.GET)
        return context


class GatewayHealthView(APIView):
    """Reports health of Django control plane and FastAPI inference service."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        bridge = FastAPIBridge()
        fastapi_status: dict[str, object]
        try:
            fastapi_status = bridge.get_json("/api/v1/health")
        except FastAPIBridgeError as exc:
            fastapi_status = {"status": "unreachable", "detail": exc.detail}

        return Response(
            {
                "status": "ok",
                "django": "online",
                "fastapi": fastapi_status,
            }
        )


class GatewayModelsView(APIView):
    """Forwards model metadata query to FastAPI ai_engine."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        bridge = FastAPIBridge()
        try:
            return Response(bridge.get_json("/api/v1/models"))
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


class DashboardOverviewView(APIView):
    """Aggregated control-plane state for Vue and React dashboards."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        quota = get_or_create_quota(request.user)
        sub = get_or_create_subscription(request.user)
        recent_tx = Transaction.objects.filter(user=request.user)[:10]
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        verification = verify_user_account_state(request.user, reconcile=False)

        bridge = FastAPIBridge()
        try:
            models_data = bridge.get_json("/api/v1/models")
        except FastAPIBridgeError:
            models_data = []

        return Response(
            {
                "user": UserProfileSerializer(profile).data,
                "quota": UserQuotaSerializer(quota).data,
                "subscription": SubscriptionSerializer(sub).data if sub else None,
                "recent_transactions": TransactionSerializer(recent_tx, many=True).data,
                "verification": verification,
                "models": models_data,
                "fastapi_base_url": settings.FASTAPI_BASE_URL,
            }
        )


class ProfileMeView(APIView):
    """Read or update the authenticated user's profile and AI studio preferences."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)

    def patch(self, request: Request) -> Response:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileListView(APIView):
    """List workspace profiles (all users for superusers/staff, own profile otherwise)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        if request.user.is_superuser or request.user.is_staff:
            User = get_user_model()
            profiles = [
                UserProfile.objects.get_or_create(user=u)[0]
                for u in User.objects.order_by("id")
            ]
        else:
            profiles = [UserProfile.objects.get_or_create(user=request.user)[0]]
        return Response(UserProfileSerializer(profiles, many=True).data)


class AnalyticsOverviewView(APIView):
    """Aggregated PostgreSQL usage telemetry, tier/task breakdown, and 7-day analytics."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        quota = get_or_create_quota(request.user)
        logs_qs = QuotaUsageLog.objects.filter(user=request.user)
        agg = logs_qs.aggregate(
            total_requests=Count("id"),
            avg_latency_ms=Avg("latency_ms"),
        )

        tier_rows = {
            row["model_tier"]: row
            for row in logs_qs.values("model_tier").annotate(
                requests=Count("id"),
                credits=Sum("credits_consumed"),
                avg_latency_ms=Avg("latency_ms"),
            )
        }
        by_tier = [
            {
                "tier": tier,
                "requests": int(tier_rows.get(tier, {}).get("requests") or 0),
                "credits": int(tier_rows.get(tier, {}).get("credits") or 0),
                "avg_latency_ms": round(float(tier_rows.get(tier, {}).get("avg_latency_ms") or 0.0), 2),
            }
            for tier in ("flash", "pro", "advance")
        ]

        task_rows = {
            row["task_type"]: row
            for row in logs_qs.values("task_type").annotate(
                requests=Count("id"),
                credits=Sum("credits_consumed"),
                avg_latency_ms=Avg("latency_ms"),
            )
        }
        by_task = [
            {
                "task": task_name,
                "requests": int(task_rows.get(task_name, {}).get("requests") or 0),
                "credits": int(task_rows.get(task_name, {}).get("credits") or 0),
                "avg_latency_ms": round(float(task_rows.get(task_name, {}).get("avg_latency_ms") or 0.0), 2),
            }
            for task_name in ("chat", "images", "video", "code", "audio", "rag")
        ]

        today = timezone.localdate()
        start_day = today - timedelta(days=6)
        day_rows = {
            row["day"]: row
            for row in logs_qs.filter(created_at__date__gte=start_day)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                requests=Count("id"),
                credits=Sum("credits_consumed"),
                avg_latency_ms=Avg("latency_ms"),
            )
        }
        daily_activity = []
        for offset in range(7):
            day = start_day + timedelta(days=offset)
            row = day_rows.get(day, {})
            daily_activity.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%b %d"),
                    "requests": int(row.get("requests") or 0),
                    "credits": int(row.get("credits") or 0),
                    "avg_latency_ms": round(float(row.get("avg_latency_ms") or 0.0), 2),
                }
            )

        recent_logs = [
            {
                "id": log.id,
                "model_tier": log.model_tier,
                "task_type": log.task_type,
                "credits_consumed": log.credits_consumed,
                "latency_ms": round(float(log.latency_ms), 2),
                "endpoint": log.endpoint,
                "created_at": log.created_at,
            }
            for log in logs_qs[:12]
        ]

        return Response(
            {
                "summary": {
                    "total_requests": int(agg.get("total_requests") or 0),
                    "used_credits": quota.used_credits,
                    "remaining_credits": quota.remaining_credits,
                    "total_credits": quota.total_credits,
                    "daily_requests": quota.daily_requests,
                    "max_daily_requests": quota.max_daily_requests,
                    "avg_latency_ms": round(float(agg.get("avg_latency_ms") or 0.0), 2),
                    "total_conversations": Conversation.objects.filter(user=request.user).count(),
                    "total_messages": ConversationMessage.objects.filter(conversation__user=request.user).count(),
                    "total_agent_runs": AgentRun.objects.filter(user=request.user).count(),
                },
                "by_tier": by_tier,
                "by_task": by_task,
                "daily_activity": daily_activity,
                "recent_logs": recent_logs,
            }
        )


class ConversationListCreateView(APIView):
    """List user conversations or start a new persistent conversation thread."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        convs = Conversation.objects.filter(user=request.user).prefetch_related("messages")
        return Response(ConversationSummarySerializer(convs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ConversationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv = serializer.save(user=request.user)
        return Response(ConversationDetailSerializer(conv).data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """Inspect, rename, or delete a single user-owned conversation."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        conv = _user_conversation_or_404(request.user, pk)
        return Response(ConversationDetailSerializer(conv).data)

    def patch(self, request: Request, pk: int) -> Response:
        conv = _user_conversation_or_404(request.user, pk)
        serializer = ConversationWriteSerializer(conv, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ConversationDetailSerializer(conv).data)

    def delete(self, request: Request, pk: int) -> Response:
        conv = _user_conversation_or_404(request.user, pk)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GatewayGenerateView(APIView):
    """Unified Django gateway forwarding multimodal prompts with conversation history & quota."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request, task: str) -> Response:
        target_endpoint = TASK_FASTAPI_ENDPOINTS.get(task)
        if target_endpoint is None:
            return Response(
                {"detail": f"Unsupported generation task '{task}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GatewayGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        conversation_id = data.pop("conversation_id", None)
        explicit_messages = data.pop("messages", None)

        conversation: Conversation | None = None
        if conversation_id is not None:
            conversation = _user_conversation_or_404(request.user, conversation_id)

        payload = {k: v for k, v in data.items() if v is not None}
        tier = payload.get("tier", "flash")
        expected_cost = estimate_request_cost(tier, task)

        if explicit_messages:
            payload["messages"] = explicit_messages
        elif conversation is not None:
            history = list(conversation.messages.order_by("-id")[:20])
            history.reverse()
            payload["messages"] = [
                {"role": m.role, "content": m.content}
                for m in history
                if m.role in ("system", "user", "assistant")
            ]

        if conversation is not None:
            payload["conversation_id"] = conversation.id
            if not payload.get("system_prompt") and conversation.system_prompt:
                payload["system_prompt"] = conversation.system_prompt

        try:
            check_user_quota(request.user, expected_cost)
        except InsufficientQuotaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        bridge = FastAPIBridge(timeout=90.0)
        try:
            result = bridge.post_json(target_endpoint, payload)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        credits_used = int(result.get("credits_used", expected_cost))
        latency_ms = float(result.get("diagnostics", {}).get("latency_ms", 0.0))

        try:
            updated_quota = consume_user_quota(
                user=request.user,
                credits=credits_used,
                model_tier=tier,
                task_type=task,
                endpoint=f"/api/v1/generate/{task}/",
                latency_ms=latency_ms,
            )
        except InsufficientQuotaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        if conversation is None:
            conversation = Conversation.objects.create(
                user=request.user,
                title=_auto_title(payload["prompt"]),
                task=task,
                tier=tier,
                system_prompt=payload.get("system_prompt") or "",
            )
        else:
            if conversation.title == "New Conversation":
                conversation.title = _auto_title(payload["prompt"])
            conversation.task = task
            conversation.tier = tier
            conversation.save()

        meta = payload.get("metadata") or {}
        raw_user_media = ""
        if isinstance(meta, dict):
            raw_user_media = str(meta.get("reference_image_base64") or "")
            if not raw_user_media and isinstance(meta.get("reference_frames_base64"), list) and meta["reference_frames_base64"]:
                raw_user_media = str(meta["reference_frames_base64"][0] or "")
        user_preview = ""
        user_mime = ""
        if raw_user_media:
            if raw_user_media.startswith("data:") and "," in raw_user_media:
                header_part, user_preview = raw_user_media.split(",", 1)
                user_mime = header_part.split(";")[0].replace("data:", "").strip() or "image/png"
            else:
                user_preview = raw_user_media
                user_mime = str(meta.get("reference_mime_type") or "image/png")
            if len(user_preview) > 450000:
                user_preview = ""
                user_mime = ""

        ConversationMessage.objects.create(
            conversation=conversation,
            role="user",
            content=payload["prompt"],
            task=task,
            tier=tier,
            preview_base64=user_preview,
            mime_type=user_mime,
        )
        assistant_content = result.get("text") or result.get("code") or f"Generated {task} output"
        ConversationMessage.objects.create(
            conversation=conversation,
            role="assistant",
            content=str(assistant_content),
            task=task,
            tier=tier,
            backend_used=str(result.get("diagnostics", {}).get("backend_used", "")),
            code=str(result.get("code") or ""),
            language=str(result.get("language") or ""),
            artifact_url=str(result.get("artifact_url") or ""),
            preview_base64=str(result.get("preview_base64") or ""),
            mime_type=str(result.get("mime_type") or ""),
            credits_used=credits_used,
            latency_ms=latency_ms,
            intent=str(result.get("extra", {}).get("intent", "")),
        )

        result["conversation_id"] = conversation.id
        result["conversation_title"] = conversation.title
        result["quota"] = UserQuotaSerializer(updated_quota).data
        return Response(result, status=status.HTTP_200_OK)


def _collect_training_samples(
    user,
    explicit_samples: list[dict],
    include_conversations: bool,
) -> list[dict]:
    """Merge persisted DB samples, request inline samples, and optional conversation Q&A turns."""
    merged: list[dict] = [
        {
            "prompt": rec.prompt[:4000],
            "response": rec.response[:16000],
            "intent": rec.intent or "general",
            "task": rec.task or "chat",
        }
        for rec in TrainingSampleRecord.objects.filter(user=user, is_active=True)[:25000]
    ]
    merged.extend(explicit_samples)
    if include_conversations:
        convs = Conversation.objects.filter(user=user).prefetch_related("messages")[:10]
        for conv in convs:
            msgs = list(conv.messages.all())
            for idx in range(len(msgs) - 1):
                if msgs[idx].role == "user" and msgs[idx + 1].role == "assistant":
                    merged.append(
                        {
                            "prompt": msgs[idx].content[:4000],
                            "response": msgs[idx + 1].content[:16000],
                            "intent": msgs[idx + 1].intent or "general",
                            "task": msgs[idx].task or "chat",
                        }
                    )
    return merged


def _build_train_payload(request: Request) -> tuple[dict, bool]:
    serializer = GatewayTrainSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    include_conversations = bool(data.pop("include_recent_conversations", False))
    data["samples"] = _collect_training_samples(
        user=request.user,
        explicit_samples=list(data.get("samples", [])),
        include_conversations=include_conversations,
    )
    payload = {k: v for k, v in data.items() if v is not None}
    return payload, include_conversations


class GatewayTrainView(APIView):
    """Protected Django gateway triggering and inspecting single-tier FastAPI ai_engine training."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        bridge = FastAPIBridge()
        try:
            return Response(bridge.get_json("/api/v1/train/status"))
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

    def post(self, request: Request) -> Response:
        payload, _ = _build_train_payload(request)
        bridge = FastAPIBridge(timeout=300.0)
        try:
            res = bridge.post_json("/api/v1/train", payload)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        TrainingRun.objects.create(
            user=request.user,
            training_id=str(res.get("training_id", "")),
            scope="single",
            tier=str(res.get("tier", payload.get("tier", "flash"))),
            backend=str(payload.get("backend") or "hybrid"),
            epochs=int(payload.get("epochs", 8)),
            learning_rate=float(payload.get("learning_rate", 0.012)),
            dataset_size=int(res.get("dataset_size", 0)),
            learned_intents=list(res.get("learned_intents", [])),
            backends_trained=list(res.get("backends_trained", [])),
            duration_ms=float(res.get("duration_ms", 0.0)),
            status="completed",
        )
        return Response(res, status=status.HTTP_200_OK)


class GatewayTrainAllView(APIView):
    """Train Flash, Pro, and Advance tiers across available neural backends and log to PostgreSQL."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        payload, _ = _build_train_payload(request)
        bridge = FastAPIBridge(timeout=600.0)
        try:
            res = bridge.post_json("/api/v1/train/all", payload)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        for tier_res in res.get("tier_results", []):
            TrainingRun.objects.create(
                user=request.user,
                training_id=str(tier_res.get("training_id") or res.get("training_id", "")),
                scope="all",
                tier=str(tier_res.get("tier", "flash")),
                backend=str(payload.get("backend") or "hybrid"),
                epochs=int(payload.get("epochs", 8)),
                learning_rate=float(payload.get("learning_rate", 0.012)),
                dataset_size=int(tier_res.get("dataset_size", res.get("dataset_size", 0))),
                learned_intents=list(tier_res.get("learned_intents", [])),
                backends_trained=list(tier_res.get("backends_trained", [])),
                duration_ms=float(tier_res.get("duration_ms", 0.0)),
                status="completed",
            )
        return Response(res, status=status.HTTP_200_OK)


class TrainingSampleListCreateView(APIView):
    """List or create persistent custom training samples in PostgreSQL."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        samples = TrainingSampleRecord.objects.filter(user=request.user)
        return Response(TrainingSampleRecordSerializer(samples, many=True).data)

    def post(self, request: Request) -> Response:
        raw_items = None
        if isinstance(request.data, list):
            raw_items = request.data
        elif isinstance(request.data, dict) and isinstance(request.data.get("samples"), list):
            raw_items = request.data["samples"]

        if raw_items is not None:
            serializer = TrainingSampleRecordSerializer(data=raw_items, many=True)
            serializer.is_valid(raise_exception=True)
            objs = [
                TrainingSampleRecord(user=request.user, **item)
                for item in serializer.validated_data
            ]
            created = TrainingSampleRecord.objects.bulk_create(objs, batch_size=500)
            return Response(
                {
                    "created": len(created),
                    "samples": TrainingSampleRecordSerializer(created[:100], many=True).data,
                },
                status=status.HTTP_201_CREATED,
            )

        serializer = TrainingSampleRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save(user=request.user)
        return Response(TrainingSampleRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class TrainingSampleDetailView(APIView):
    """Update or delete an individual user-owned training sample."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        record = get_object_or_404(TrainingSampleRecord, pk=pk, user=request.user)
        serializer = TrainingSampleRecordSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request: Request, pk: int) -> Response:
        record = get_object_or_404(TrainingSampleRecord, pk=pk, user=request.user)
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrainingRunHistoryView(APIView):
    """Return user's persisted training run history from PostgreSQL."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            TrainingRun.objects.all()
            if (request.user.is_staff or request.user.is_superuser)
            else TrainingRun.objects.filter(user=request.user)
        )
        runs = qs[:50]
        return Response(TrainingRunSerializer(runs, many=True).data)


class GatewayTrainEvaluateView(APIView):
    """Evaluate trained neural intent prediction & sample retrieval for a prompt."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = GatewayTrainEvaluateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {k: v for k, v in serializer.validated_data.items() if v is not None}
        bridge = FastAPIBridge(timeout=60.0)
        try:
            return Response(bridge.post_json("/api/v1/train/evaluate", payload), status=status.HTTP_200_OK)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


class GatewayTrainCheckpointsView(APIView):
    """List saved weight checkpoints on disk via FastAPI ai_engine."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        bridge = FastAPIBridge()
        try:
            return Response(bridge.get_json("/api/v1/train/checkpoints"))
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


class GatewayTrainResetView(APIView):
    """Clear persisted checkpoints & caches via FastAPI ai_engine."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        bridge = FastAPIBridge()
        try:
            return Response(bridge.post_json("/api/v1/train/reset", {}), status=status.HTTP_200_OK)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


class AccountVerifyView(APIView):
    """Verify and optionally reconcile user profile, billing subscription, and balance ledger."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        reconcile = str(request.query_params.get("reconcile", "")).lower() in ("1", "true", "yes")
        report = verify_user_account_state(request.user, reconcile=reconcile)
        return Response(report, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        reconcile_val = request.data.get("reconcile", True)
        reconcile = reconcile_val if isinstance(reconcile_val, bool) else str(reconcile_val).lower() in ("1", "true", "yes")
        report = verify_user_account_state(request.user, reconcile=reconcile)
        return Response(report, status=status.HTTP_200_OK)


class SecretKeyListCreateView(APIView):
    """List or generate per-user API secret keys (`sk_tblinc_...`)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        keys = SecretKey.objects.filter(user=request.user)
        return Response(SecretKeySerializer(keys, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = SecretKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance, raw_secret = SecretKey.create_key(
            user=request.user,
            name=serializer.validated_data.get("name") or "Default Secret Key",
        )
        data = dict(SecretKeySerializer(instance).data)
        data["secret_key"] = raw_secret
        return Response(data, status=status.HTTP_201_CREATED)


class SecretKeyDetailView(APIView):
    """Toggle/rename or delete a user-owned API secret key."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        key_obj = get_object_or_404(SecretKey, pk=pk, user=request.user)
        updated_fields: list[str] = []
        if "is_active" in request.data:
            key_obj.is_active = bool(request.data["is_active"])
            updated_fields.append("is_active")
        if "name" in request.data and str(request.data["name"]).strip():
            key_obj.name = str(request.data["name"]).strip()[:80]
            updated_fields.append("name")
        if updated_fields:
            key_obj.save(update_fields=updated_fields)
        return Response(SecretKeySerializer(key_obj).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, pk: int) -> Response:
        key_obj = get_object_or_404(SecretKey, pk=pk, user=request.user)
        key_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GatewayAudioTranscribeView(APIView):
    """Transcribe speech audio via Whisper through FastAPI gateway."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        bridge = FastAPIBridge(timeout=60.0)
        try:
            return Response(bridge.post_json("/api/v1/audio/transcribe", request.data), status=status.HTTP_200_OK)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


class GatewayAudioAnalyzeView(APIView):
    """Perform acoustic analysis via Librosa/Soundfile through FastAPI gateway."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        bridge = FastAPIBridge(timeout=30.0)
        try:
            return Response(bridge.post_json("/api/v1/audio/analyze", request.data), status=status.HTTP_200_OK)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_root_router(request: Request, format=None) -> Response:
    """
    tblinc AI-Model Unified Platform API Router.
    Full directory of all control plane REST endpoints, auth, and compute gateways.
    """
    base = request.build_absolute_uri("/").rstrip("/")
    return Response({
        "service": "AI-Model Platform Control Plane",
        "status": "healthy",
        "version": "1.0.0",
        "engine": "FastAPI Neural Compute Gateway (:8001)",
        "graphql": "PostGraphile GraphQL Gateway (:5000/graphql)",
        "endpoints": {
            "root": f"{base}/api/",
            "v1_root": f"{base}/api/v1/",
            "health": f"{base}/api/v1/health/",
            "models": f"{base}/api/v1/models/",
            "dashboard": f"{base}/api/v1/dashboard/",
            "analytics": f"{base}/api/v1/analytics/",
            "verify": f"{base}/api/v1/verify/",
            "profile": f"{base}/api/v1/profile/",
            "profiles": f"{base}/api/v1/profiles/",
            "keys": f"{base}/api/v1/keys/",
            "api_keys": f"{base}/api/v1/api-keys/",
            "conversations": f"{base}/api/v1/conversations/",
            "train": f"{base}/api/v1/train/",
            "train_all": f"{base}/api/v1/train/all/",
            "train_samples": f"{base}/api/v1/train/samples/",
            "train_history": f"{base}/api/v1/train/history/",
            "train_evaluate": f"{base}/api/v1/train/evaluate/",
            "train_checkpoints": f"{base}/api/v1/train/checkpoints/",
            "train_reset": f"{base}/api/v1/train/reset/",
            "audio_transcribe": f"{base}/api/v1/audio/transcribe/",
            "audio_analyze": f"{base}/api/v1/audio/analyze/",
            "rag_scrape": f"{base}/api/v1/rag/scrape/",
            "generate_chat": f"{base}/api/v1/generate/chat/",
            "generate_code": f"{base}/api/v1/generate/code/",
            "generate_images": f"{base}/api/v1/generate/images/",
            "generate_video": f"{base}/api/v1/generate/video/",
            "generate_audio": f"{base}/api/v1/generate/audio/",
            "auth_users": f"{base}/api/auth/users/",
            "auth_jwt_create": f"{base}/api/auth/jwt/create/",
            "auth_jwt_refresh": f"{base}/api/auth/jwt/refresh/",
            "billing_plans": f"{base}/api/billing/plans/",
            "billing_subscription": f"{base}/api/billing/subscription/",
            "billing_invoices": f"{base}/api/billing/invoices/",
            "transactions": f"{base}/api/transactions/",
            "quota": f"{base}/api/quota/me/",
            "agent_profiles": f"{base}/api/agent/profiles/",
            "agent_runs": f"{base}/api/agent/runs/",
            "agent_execute": f"{base}/api/agent/execute/",
        },
    }, status=status.HTTP_200_OK)


class ApiRootIndexView(APIView):
    """API Root directory mapping all available platform REST endpoints."""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request, format=None) -> Response:
        return api_root_router(request, format=format)


class GatewayRagScrapeView(APIView):
    """Scrape web content via BeautifulSoup4 & index into ChromaDB through FastAPI gateway."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        bridge = FastAPIBridge(timeout=45.0)
        try:
            return Response(bridge.post_json("/api/v1/rag/scrape", request.data), status=status.HTTP_200_OK)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

