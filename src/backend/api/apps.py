"""API app configuration."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """App config for Django-to-FastAPI gateway and web portal."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

