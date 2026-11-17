"""PostgreSQL models storing persistent multi-turn AI conversations and messages."""

from __future__ import annotations

import hashlib
import secrets
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """User-owned multi-turn conversation thread across Flash, Pro, and Advance."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=160, default="New Conversation")
    task = models.CharField(max_length=16, default="chat")
    tier = models.CharField(max_length=16, default="flash")
    system_prompt = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return f"Conversation({self.id}, user={self.user_id}, title={self.title!r})"


class ConversationMessage(models.Model):
    """Single user, assistant, or system turn persisted inside a Conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, default="user")
    content = models.TextField()
    task = models.CharField(max_length=16, default="chat")
    tier = models.CharField(max_length=16, default="flash")
    backend_used = models.CharField(max_length=64, blank=True, default="")
    code = models.TextField(blank=True, default="")
    language = models.CharField(max_length=32, blank=True, default="")
    artifact_url = models.CharField(max_length=255, blank=True, default="")
    preview_base64 = models.TextField(blank=True, default="")
    mime_type = models.CharField(max_length=64, blank=True, default="")
    credits_used = models.PositiveIntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)
    intent = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"ConversationMessage({self.id}, conv={self.conversation_id}, role={self.role})"


class UserProfile(models.Model):
    """Persistent account profile, workspace role metadata, and AI defaults per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=120, blank=True, default="")
    avatar = models.TextField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    role_title = models.CharField(max_length=80, blank=True, default="AI Builder")
    organization = models.CharField(max_length=120, blank=True, default="")
    default_tier = models.CharField(max_length=16, default="flash")
    default_task = models.CharField(max_length=16, default="chat")
    default_system_prompt = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"UserProfile(user={self.user_id}, display_name={self.display_name!r})"


class TrainingSampleRecord(models.Model):
    """Persistent user-curated training sample stored in PostgreSQL for fine-tuning."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_samples",
    )
    prompt = models.TextField()
    response = models.TextField()
    intent = models.CharField(max_length=64, default="general")
    task = models.CharField(max_length=16, default="chat")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return f"TrainingSampleRecord({self.id}, intent={self.intent!r}, task={self.task})"


class TrainingRun(models.Model):
    """Persistent audit ledger of model training sessions across Flash, Pro, and Advance."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_runs",
    )
    training_id = models.CharField(max_length=64, db_index=True)
    scope = models.CharField(max_length=16, default="single")
    tier = models.CharField(max_length=16, default="flash")
    backend = models.CharField(max_length=24, default="hybrid")
    epochs = models.PositiveIntegerField(default=14)
    learning_rate = models.FloatField(default=0.012)
    dataset_size = models.PositiveIntegerField(default=0)
    learned_intents = models.JSONField(default=list, blank=True)
    backends_trained = models.JSONField(default=list, blank=True)
    duration_ms = models.FloatField(default=0.0)
    status = models.CharField(max_length=24, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"TrainingRun({self.training_id[:8]}, {self.scope}/{self.tier}, {self.dataset_size} samples)"


class SecretKey(models.Model):
    """Hashed per-user API secret key supporting programmatic platform authentication."""

    SECRET_PREFIX = "sk_tblinc_"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="secret_keys",
    )
    name = models.CharField(max_length=80, default="Default Secret Key")
    key_prefix = models.CharField(max_length=24, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @classmethod
    def hash_secret(cls, raw_key: str) -> str:
        """Compute deterministic SHA-256 digest of a raw API secret key."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def create_key(cls, user, name: str = "Default Secret Key") -> tuple["SecretKey", str]:
        """Generate a new cryptographically random secret key and store its hash."""
        raw_secret = f"{cls.SECRET_PREFIX}{secrets.token_urlsafe(32)}"
        instance = cls.objects.create(
            user=user,
            name=(name or "Default Secret Key").strip()[:80] or "Default Secret Key",
            key_prefix=raw_secret[:18],
            key_hash=cls.hash_secret(raw_secret),
        )
        return instance, raw_secret

    def __str__(self) -> str:
        return f"SecretKey({self.user_id}, {self.name!r}, {self.key_prefix}...)"

