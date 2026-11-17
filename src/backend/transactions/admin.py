"""Admin registrations for transactions."""

from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_id",
        "user",
        "tx_type",
        "payment_method",
        "tnxid",
        "credits_delta",
        "amount_bdt",
        "amount_usd",
        "balance_after",
        "created_at",
    )
    list_filter = ("tx_type", "currency", "payment_method", "model_tier", "task_type")
    search_fields = ("reference_id", "tnxid", "user__username", "description")

