"""Agent app configuration."""

from django.apps import AppConfig


class AgentConfig(AppConfig):
    """App config for customizable AI agent profiles and execution logs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "Agent"
    verbose_name = "AI Agents"

