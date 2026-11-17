"""Billing app configuration."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """App config for plans, subscriptions, and invoices."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "billing"

