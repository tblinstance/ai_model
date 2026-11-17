"""Billing models for subscription tiers, active subscriptions, and invoices."""

from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Plan(models.Model):
    """Subscription tier configuring monthly credits, rate limits, and allowed models."""

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    monthly_price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_credits = models.PositiveIntegerField(default=250)
    daily_request_limit = models.PositiveIntegerField(default=250)
    allowed_tiers = models.JSONField(default=list)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["monthly_price_usd"]

    def __str__(self) -> str:
        return f"{self.name} (${self.monthly_price_usd}/mo)"


class Subscription(models.Model):
    """Active subscription linking a user to a billing plan."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Canceled"
        PAST_DUE = "past_due", "Past Due"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    renews_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.user} -> {self.plan.name} ({self.status})"


class Invoice(models.Model):
    """Billing invoice generated on subscription activation or renewal."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    invoice_number = models.CharField(max_length=48, unique=True, blank=True)
    currency = models.CharField(max_length=8, default="USD", db_default="USD")
    amount_usd = models.DecimalField(max_digits=8, decimal_places=2)
    amount_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_default=0)
    payment_method = models.CharField(max_length=24, blank=True, default="", db_default="")
    tnxid = models.CharField(max_length=64, blank=True, default="", db_default="", db_index=True)
    credits_granted = models.PositiveIntegerField()
    status = models.CharField(max_length=24, default="paid")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tnxid"],
                condition=~Q(tnxid=""),
                name="uniq_invoice_nonempty_tnxid",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.invoice_number} | {self.user} | ${self.amount_usd}"


class MfsPaymentRequest(models.Model):
    """Member-submitted BDT MFS payment awaiting Admin verification and approval."""

    class Kind(models.TextChoices):
        CREDITS = "credits", "Credit Pack"
        PLAN = "plan", "Plan Subscription"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfs_payment_requests",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True)
    credits_requested = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=8, default="BDT", db_default="BDT")
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_default=0)
    payment_method = models.CharField(max_length=24)
    tnxid = models.CharField(max_length=64, unique=True, db_index=True)
    sender_number = models.CharField(max_length=32, blank=True, default="", db_default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_default=Status.PENDING,
    )
    admin_note = models.CharField(max_length=255, blank=True, default="", db_default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_mfs_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mfs_requests",
    )
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mfs_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"REQ#{self.pk} | {self.user} | {self.payment_method.upper()} {self.tnxid} ({self.status})"


