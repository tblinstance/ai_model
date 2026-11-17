"""Transaction ledger models."""

from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q


class Transaction(models.Model):
    """Immutable financial and credit ledger entry for user activity."""

    class TxType(models.TextChoices):
        CREDIT_PURCHASE = "credit_purchase", "Credit Purchase"
        USAGE_DEDUCTION = "usage_deduction", "AI Usage Deduction"
        SUBSCRIPTION = "subscription", "Plan Subscription"
        BONUS = "bonus", "Starter / Bonus Credits"
        REFUND = "refund", "Refund"

    class PaymentMethod(models.TextChoices):
        BKASH = "bkash", "bKash"
        NAGAD = "nagad", "Nagad"
        ROCKET = "rocket", "Rocket"
        UPAY = "upay", "Upay"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    tx_type = models.CharField(max_length=32, choices=TxType.choices)
    currency = models.CharField(max_length=8, default="USD", db_default="USD")
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_default=0)
    payment_method = models.CharField(
        max_length=24,
        choices=PaymentMethod.choices,
        blank=True,
        default="",
        db_default="",
    )
    tnxid = models.CharField(max_length=64, blank=True, default="", db_default="", db_index=True)
    credits_delta = models.IntegerField()
    balance_after = models.IntegerField(default=0)
    model_tier = models.CharField(max_length=24, blank=True, default="")
    task_type = models.CharField(max_length=24, blank=True, default="")
    reference_id = models.CharField(
        max_length=64,
        unique=True,
        default="",
        blank=True,
    )
    description = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tnxid"],
                condition=~Q(tnxid=""),
                name="uniq_transaction_nonempty_tnxid",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.reference_id:
            self.reference_id = f"tx_{uuid.uuid4().hex[:16]}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user} | {self.tx_type} ({self.credits_delta:+d})"

