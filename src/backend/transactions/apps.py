"""Transactions app configuration."""

from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """App config for billing and credit transaction ledger."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "transactions"

