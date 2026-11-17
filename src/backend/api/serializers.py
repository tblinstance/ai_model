"""Serializers for Django API gateway, conversations, and neural training."""

from __future__ import annotations

from rest_framework import serializers

from billing.models import Subscription
from quota.services import get_or_create_quota
from .models import (
    Conversation,
    ConversationMessage,
    SecretKey,
    TrainingRun,
    TrainingSampleRecord,
    UserProfile,
)


class UserProfileSerializer(serializers.ModelSerializer):
    """Unified serializer combining Django User fields and persistent UserProfile preferences."""

    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True, max_length=150)
    is_superuser = serializers.BooleanField(source="user.is_superuser", read_only=True)
    is_staff = serializers.BooleanField(source="user.is_staff", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    default_tier = serializers.ChoiceField(choices=["flash", "pro", "advance"], required=False)
    default_task = serializers.ChoiceField(choices=["chat", "images", "video", "code", "audio", "rag"], required=False)
    remaining_credits = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    conversation_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "avatar",
            "bio",
            "role_title",
            "organization",
            "default_tier",
            "default_task",
            "default_system_prompt",
            "is_superuser",
            "is_staff",
            "date_joined",
            "remaining_credits",
            "plan_name",
            "conversation_count",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_remaining_credits(self, obj: UserProfile) -> int:
        return get_or_create_quota(obj.user).remaining_credits

    def get_plan_name(self, obj: UserProfile) -> str:
        sub = Subscription.objects.filter(user=obj.user).select_related("plan").first()
        return sub.plan.name if sub else "Free"

    def get_conversation_count(self, obj: UserProfile) -> int:
        return obj.user.conversations.count()

    def update(self, instance: UserProfile, validated_data: dict) -> UserProfile:
        user_data = validated_data.pop("user", {})
        user = instance.user
        user_dirty = False
        for field in ("email", "first_name", "last_name"):
            if field in user_data:
                setattr(user, field, user_data[field])
                user_dirty = True
        if user_dirty:
            user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChatTurnInputSerializer(serializers.Serializer):
    """Single message turn passed as context to FastAPI ai_engine."""

    role = serializers.ChoiceField(choices=["system", "user", "assistant"], default="user")
    content = serializers.CharField(min_length=1, max_length=16000)


class GatewayGenerateSerializer(serializers.Serializer):
    """Unified input serializer for Chat, Images, Video, and Code proxy endpoints."""

    prompt = serializers.CharField(min_length=1, max_length=16000)
    tier = serializers.ChoiceField(choices=["flash", "pro", "advance"], default="flash")
    backend = serializers.ChoiceField(
        choices=["numpy", "pytorch", "tensorflow", "keras", "hybrid"],
        required=False,
        allow_null=True,
    )
    conversation_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    messages = ChatTurnInputSerializer(many=True, required=False)
    system_prompt = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    language = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    temperature = serializers.FloatField(min_value=0.0, max_value=2.0, default=0.7)
    max_tokens = serializers.IntegerField(min_value=16, max_value=8192, default=512)
    width = serializers.IntegerField(min_value=64, max_value=1280, required=False, allow_null=True)
    height = serializers.IntegerField(min_value=64, max_value=1024, required=False, allow_null=True)
    frames = serializers.IntegerField(min_value=4, max_value=360, required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(min_value=1, max_value=3600, required=False, allow_null=True)
    seed = serializers.IntegerField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, default=dict)


class ConversationMessageSerializer(serializers.ModelSerializer):
    """Serializes individual persisted conversation messages."""

    class Meta:
        model = ConversationMessage
        fields = [
            "id",
            "role",
            "content",
            "task",
            "tier",
            "backend_used",
            "code",
            "language",
            "artifact_url",
            "preview_base64",
            "mime_type",
            "credits_used",
            "latency_ms",
            "intent",
            "created_at",
        ]
        read_only_fields = fields


class ConversationSummarySerializer(serializers.ModelSerializer):
    """Compact summary serializer for sidebar/thread list views."""

    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "task",
            "tier",
            "system_prompt",
            "message_count",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, obj: Conversation) -> int:
        return obj.messages.count()

    def get_last_message(self, obj: Conversation) -> str:
        msgs = list(obj.messages.all())
        if not msgs:
            return ""
        text = msgs[-1].content.strip().replace("\n", " ")
        return text[:96] + ("..." if len(text) > 96 else "")


class ConversationDetailSerializer(ConversationSummarySerializer):
    """Full conversation serializer including chronological turns."""

    messages = ConversationMessageSerializer(many=True, read_only=True)

    class Meta(ConversationSummarySerializer.Meta):
        fields = [*ConversationSummarySerializer.Meta.fields, "messages"]


class ConversationWriteSerializer(serializers.ModelSerializer):
    """Serializer used when creating or updating a Conversation."""

    class Meta:
        model = Conversation
        fields = ["title", "task", "tier", "system_prompt"]
        extra_kwargs = {
            "title": {"required": False},
            "task": {"required": False},
            "tier": {"required": False},
            "system_prompt": {"required": False},
        }


class TrainingSampleInputSerializer(serializers.Serializer):
    """Single instruction/response training sample."""

    prompt = serializers.CharField(min_length=1, max_length=4000)
    response = serializers.CharField(min_length=1, max_length=16000)
    intent = serializers.CharField(min_length=1, max_length=64, default="general")
    task = serializers.ChoiceField(choices=["chat", "images", "video", "code", "audio", "rag"], default="chat")


class GatewayTrainSerializer(serializers.Serializer):
    """Validated payload forwarded from Django gateway to FastAPI /api/v1/train."""

    tier = serializers.ChoiceField(choices=["flash", "pro", "advance"], default="flash")
    backend = serializers.ChoiceField(
        choices=["numpy", "pytorch", "tensorflow", "keras", "hybrid"],
        required=False,
        allow_null=True,
    )
    epochs = serializers.IntegerField(min_value=1, max_value=100, default=8)
    learning_rate = serializers.FloatField(min_value=0.0001, max_value=0.5, default=0.012)
    include_builtin_dataset = serializers.BooleanField(default=True)
    include_recent_conversations = serializers.BooleanField(default=False)
    samples = TrainingSampleInputSerializer(many=True, required=False, default=list)
    save_checkpoint = serializers.BooleanField(default=True)


class TrainingSampleRecordSerializer(serializers.ModelSerializer):
    """Serializer for persistent custom training examples in PostgreSQL."""

    intent = serializers.CharField(min_length=1, max_length=64, required=False, default="general")
    task = serializers.ChoiceField(choices=["chat", "images", "video", "code", "audio", "rag"], required=False, default="chat")

    class Meta:
        model = TrainingSampleRecord
        fields = [
            "id",
            "prompt",
            "response",
            "intent",
            "task",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TrainingRunSerializer(serializers.ModelSerializer):
    """Serializer for persisted training session history rows."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TrainingRun
        fields = [
            "id",
            "training_id",
            "username",
            "scope",
            "tier",
            "backend",
            "epochs",
            "learning_rate",
            "dataset_size",
            "learned_intents",
            "backends_trained",
            "duration_ms",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class GatewayTrainEvaluateSerializer(serializers.Serializer):
    """Input serializer for evaluating model predictions against a prompt."""

    prompt = serializers.CharField(min_length=1, max_length=4000)
    tier = serializers.ChoiceField(choices=["flash", "pro", "advance"], default="flash")
    backend = serializers.ChoiceField(
        choices=["numpy", "pytorch", "tensorflow", "keras", "hybrid"],
        required=False,
        allow_null=True,
    )
    expected_intent = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    task = serializers.ChoiceField(choices=["chat", "images", "video", "code", "audio", "rag"], default="chat")


class SecretKeySerializer(serializers.ModelSerializer):
    """Read serializer for masked user API secret keys (never exposes hash)."""

    class Meta:
        model = SecretKey
        fields = [
            "id",
            "name",
            "key_prefix",
            "is_active",
            "created_at",
            "last_used_at",
        ]
        read_only_fields = fields


class SecretKeyCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new API secret key."""

    name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="Default Secret Key")
