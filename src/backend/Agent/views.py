"""REST views for managing and executing AI Agents."""

from django.db.models import Q
from django.utils.text import slugify
from rest_framework import generics, permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.fastapi_bridge import FastAPIBridge, FastAPIBridgeError
from quota.services import InsufficientQuotaError, check_user_quota, consume_user_quota, estimate_request_cost
from .models import AgentProfile, AgentRun
from .serializers import AgentProfileSerializer, AgentRunSerializer, ExecuteAgentSerializer


DEFAULT_AGENTS = [
    {
        "slug": "flash-copilot",
        "name": "Flash Code & Chat Copilot",
        "system_prompt": "Rapid architectural reasoning and clean code assistant.",
        "default_tier": "flash",
        "default_task": "code",
        "tools_enabled": ["chat", "code"],
    },
    {
        "slug": "pro-creative-director",
        "name": "Pro Visual & Video Director",
        "system_prompt": "Designs cohesive imagery and animated motion scenes.",
        "default_tier": "pro",
        "default_task": "images",
        "tools_enabled": ["images", "video", "chat"],
    },
    {
        "slug": "advance-architect",
        "name": "tblinc AI Architect",
        "system_prompt": "tblinc AI multi-stage synthesis and architecture specialist.",
        "default_tier": "advance",
        "default_task": "chat",
        "tools_enabled": ["chat", "images", "video", "code"],
    },
]


def ensure_default_agents() -> None:
    """Seed starter public Agent profiles if none exist."""
    for item in DEFAULT_AGENTS:
        AgentProfile.objects.update_or_create(slug=item["slug"], defaults=item)


class AgentProfileViewSet(viewsets.ModelViewSet):
    """List, create, update, and delete customizable Agent personas."""

    serializer_class = AgentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not AgentProfile.objects.exists():
            ensure_default_agents()
        return AgentProfile.objects.filter(Q(is_public=True) | Q(owner=self.request.user))

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        raw_slug = (serializer.validated_data.get("slug") or "").strip()
        base_slug = raw_slug or slugify(name) or "agent"
        slug = base_slug
        counter = 1
        while AgentProfile.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        serializer.save(owner=self.request.user, slug=slug)


class AgentRunListView(generics.ListAPIView):
    """List execution runs triggered by the authenticated user."""

    serializer_class = AgentRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AgentRun.objects.filter(user=self.request.user).select_related("agent")[:50]


class ExecuteAgentView(APIView):
    """Invoke FastAPI /api/v1/agent/run, enforce quota, and persist AgentRun."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ExecuteAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent = None
        if data.get("agent_id"):
            agent = AgentProfile.objects.filter(
                Q(pk=data["agent_id"]) & (Q(is_public=True) | Q(owner=request.user))
            ).first()

        tier = data.get("tier") or (agent.default_tier if agent else "pro")
        task = data.get("task") or (agent.default_task if agent else None)
        expected_cost = estimate_request_cost(tier, task)
        try:
            check_user_quota(request.user, expected_cost)
        except InsufficientQuotaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        payload = {
            "agent_name": agent.name if agent else "Custom AI Agent",
            "prompt": data["prompt"],
            "tier": tier,
            "task": task,
            "system_prompt": agent.system_prompt if agent else None,
            "backend": data.get("backend"),
        }

        bridge = FastAPIBridge()
        try:
            # Call FastAPI without forwarding auth header so Django handles quota cleanly once here
            fastapi_res = bridge.post_json("/api/v1/agent/run", payload)
        except FastAPIBridgeError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        result = fastapi_res["result"]
        resolved_task = fastapi_res["resolved_task"]
        credits_used = int(result.get("credits_used", 1))
        latency_ms = float(result.get("diagnostics", {}).get("latency_ms", 0.0))

        try:
            quota = consume_user_quota(
                user=request.user,
                credits=credits_used,
                model_tier=tier,
                task_type=resolved_task,
                endpoint="/api/agent/execute/",
                latency_ms=latency_ms,
            )
        except InsufficientQuotaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        run = AgentRun.objects.create(
            agent=agent,
            user=request.user,
            prompt=data["prompt"],
            selected_tier=tier,
            selected_task=resolved_task,
            response_text=result.get("text") or result.get("code") or "",
            artifact_url=result.get("artifact_url") or "",
            status="completed",
            credits_used=credits_used,
            latency_ms=latency_ms,
            metadata={"diagnostics": result.get("diagnostics", {})},
        )
        return Response(
            {
                "run": AgentRunSerializer(run).data,
                "result": result,
                "remaining_credits": quota.remaining_credits,
            },
            status=status.HTTP_201_CREATED,
        )
