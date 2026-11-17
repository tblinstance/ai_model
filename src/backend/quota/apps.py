"""Quota app configuration."""

from django.apps import AppConfig


class QuotaConfig(AppConfig):
    """App config wiring user quota creation signals."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "quota"

    def ready(self) -> None:
        from . import signals  # noqa: F401

