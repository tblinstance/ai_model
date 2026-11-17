"""Admin registrations for Agent models."""

from django.contrib import admin

from .models import AgentProfile, AgentRun


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "default_tier", "default_task", "is_public", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "user", "selected_tier", "selected_task", "credits_used", "status", "created_at")
    list_filter = ("selected_tier", "selected_task", "status")

