"""Django Admin registrations for AI conversations, profiles, and training telemetry."""

from django.contrib import admin

from .models import (
    Conversation,
    ConversationMessage,
    SecretKey,
    TrainingRun,
    TrainingSampleRecord,
    UserProfile,
)
from .verification import verify_user_account_state


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "task", "tier", "updated_at")
    search_fields = ("title", "user__username")
    list_filter = ("task", "tier")


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "task", "tier", "intent", "credits_used", "created_at")
    list_filter = ("role", "task", "tier", "intent")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "role_title", "default_tier", "default_task", "updated_at")
    search_fields = ("user__username", "display_name", "organization")
    actions = ["verify_selected_profiles"]

    @admin.action(description="Verify & reconcile selected users' profile, billing, and balance")
    def verify_selected_profiles(self, request, queryset) -> None:
        count = 0
        for profile in queryset.select_related("user"):
            verify_user_account_state(profile.user, reconcile=True)
            count += 1
        self.message_user(request, f"Verified & reconciled {count} user profile(s).")


@admin.register(TrainingSampleRecord)
class TrainingSampleRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "intent", "task", "is_active", "updated_at")
    search_fields = ("prompt", "response", "intent")
    list_filter = ("task", "intent", "is_active")


@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = ("id", "training_id", "user", "scope", "tier", "backend", "epochs", "dataset_size", "duration_ms", "created_at")
    list_filter = ("scope", "tier", "backend", "status")


@admin.register(SecretKey)
class SecretKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "key_prefix", "is_active", "created_at", "last_used_at")
    search_fields = ("user__username", "name", "key_prefix")
    list_filter = ("is_active",)

