"""Serializers for quota balances and usage audit logs."""

from rest_framework import serializers

from .models import QuotaUsageLog, UserQuota


class UserQuotaSerializer(serializers.ModelSerializer):
    """Read serializer for user quota status."""

    remaining_credits = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserQuota
        fields = [
            "total_credits",
            "used_credits",
            "remaining_credits",
            "daily_requests",
            "max_daily_requests",
            "last_reset_date",
            "updated_at",
        ]


class ConsumeQuotaSerializer(serializers.Serializer):
    """Input payload for internal or direct quota consumption."""

    credits = serializers.IntegerField(min_value=1, max_value=1000)
    model_tier = serializers.CharField(max_length=24, default="flash")
    task_type = serializers.CharField(max_length=24, default="chat")
    endpoint = serializers.CharField(max_length=128, default="/api/v1/chat")
    latency_ms = serializers.FloatField(min_value=0.0, default=0.0)


class QuotaUsageLogSerializer(serializers.ModelSerializer):
    """Read serializer for recent quota usage log entries."""

    class Meta:
        model = QuotaUsageLog
        fields = [
            "id",
            "endpoint",
            "model_tier",
            "task_type",
            "credits_consumed",
            "latency_ms",
            "created_at",
        ]

