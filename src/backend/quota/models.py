"""Quota balance and usage audit models."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserQuota(models.Model):
    """Tracks per-user AI credit allowance and daily rate limits."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quota",
    )
    total_credits = models.PositiveIntegerField(default=250)
    used_credits = models.PositiveIntegerField(default=0)
    daily_requests = models.PositiveIntegerField(default=0)
    max_daily_requests = models.PositiveIntegerField(default=250)
    last_reset_date = models.DateField(default=timezone.localdate)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_credits(self) -> int:
        """Return currently available credits."""
        return max(0, self.total_credits - self.used_credits)

    def __str__(self) -> str:
        return f"{self.user} | {self.remaining_credits} credits left"


class QuotaUsageLog(models.Model):
    """Per-request telemetry log for AI inference consumption."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quota_logs",
    )
    endpoint = models.CharField(max_length=128)
    model_tier = models.CharField(max_length=24, default="flash")
    task_type = models.CharField(max_length=24, default="chat")
    credits_consumed = models.PositiveIntegerField(default=1)
    latency_ms = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} | {self.model_tier}/{self.task_type} (-{self.credits_consumed})"

