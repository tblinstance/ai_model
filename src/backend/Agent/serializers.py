"""Serializers for AI agent profiles, runs, and execution payloads."""

from rest_framework import serializers

from .models import AgentProfile, AgentRun


class AgentProfileSerializer(serializers.ModelSerializer):
    """CRUD serializer for AgentProfile."""

    slug = serializers.SlugField(required=False, allow_blank=True, allow_null=True, max_length=50)

    class Meta:
        model = AgentProfile
        fields = [
            "id",
            "name",
            "slug",
            "system_prompt",
            "default_tier",
            "default_task",
            "tools_enabled",
            "is_public",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AgentRunSerializer(serializers.ModelSerializer):
    """Read serializer for historical agent runs."""

    agent_name = serializers.CharField(source="agent.name", read_only=True, default="Ad-hoc Agent")

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "agent",
            "agent_name",
            "prompt",
            "selected_tier",
            "selected_task",
            "response_text",
            "artifact_url",
            "status",
            "credits_used",
            "latency_ms",
            "metadata",
            "created_at",
        ]


class ExecuteAgentSerializer(serializers.Serializer):
    """Input payload for running an agent prompt via FastAPI ai_engine."""

    agent_id = serializers.IntegerField(required=False, allow_null=True)
    prompt = serializers.CharField(min_length=1, max_length=16000)
    tier = serializers.ChoiceField(choices=["flash", "pro", "advance"], required=False)
    task = serializers.ChoiceField(choices=["chat", "images", "video", "code"], required=False)
    backend = serializers.ChoiceField(
        choices=["numpy", "pytorch", "tensorflow", "keras", "hybrid"],
        required=False,
        allow_null=True,
    )

