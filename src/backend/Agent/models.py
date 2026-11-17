"""Agent profile and execution history models."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class AgentProfile(models.Model):
    """Configurable AI agent persona bound to a default tier and capability."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agents",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    system_prompt = models.TextField(default="You are a precise, helpful multimodal AI assistant.")
    default_tier = models.CharField(max_length=16, default="pro")
    default_task = models.CharField(max_length=16, default="chat")
    tools_enabled = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.default_tier}/{self.default_task})"


class AgentRun(models.Model):
    """Execution audit log for an Agent invocation."""

    agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_runs",
    )
    prompt = models.TextField()
    selected_tier = models.CharField(max_length=16, default="pro")
    selected_task = models.CharField(max_length=16, default="chat")
    response_text = models.TextField(blank=True, default="")
    artifact_url = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=24, default="completed")
    credits_used = models.PositiveIntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Run #{self.pk} by {self.user} ({self.status})"

