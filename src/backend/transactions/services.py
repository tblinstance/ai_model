"""Domain services for recording and summarizing user credit transactions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Sum

from .models import Transaction


def record_transaction(
    *,
    user: AbstractBaseUser,
    tx_type: str,
    credits_delta: int,
    balance_after: int,
    amount_usd: Decimal | float | int = 0,
    amount_bdt: Decimal | float | int | None = None,
    currency: str = "USD",
    payment_method: str = "",
    tnxid: str = "",
    model_tier: str = "",
    task_type: str = "",
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> Transaction:
    """Create a new transaction ledger entry with optional BDT & MFS wallet details."""
    usd_dec = Decimal(str(amount_usd)).quantize(Decimal("0.01"))
    if amount_bdt is None:
        bdt_dec = (usd_dec * Decimal("120.00")).quantize(Decimal("0.01")) if usd_dec > 0 else Decimal("0.00")
    else:
        bdt_dec = Decimal(str(amount_bdt)).quantize(Decimal("0.01"))

    return Transaction.objects.create(
        user=user,
        tx_type=tx_type,
        currency=(currency or "USD").strip().upper()[:8] or "USD",
        amount_usd=usd_dec,
        amount_bdt=bdt_dec,
        payment_method=(payment_method or "").strip().lower(),
        tnxid=(tnxid or "").strip().upper(),
        credits_delta=credits_delta,
        balance_after=balance_after,
        model_tier=model_tier,
        task_type=task_type,
        description=description,
        metadata=metadata or {},
    )


def summarize_user_transactions(user: AbstractBaseUser) -> dict[str, Any]:
    """Compute aggregate transaction totals for a user across USD and BDT."""
    qs = Transaction.objects.filter(user=user)
    spent_credits = qs.filter(credits_delta__lt=0).aggregate(total=Sum("credits_delta"))["total"] or 0
    added_credits = qs.filter(credits_delta__gt=0).aggregate(total=Sum("credits_delta"))["total"] or 0
    total_usd = qs.aggregate(total=Sum("amount_usd"))["total"] or Decimal("0.00")
    total_bdt = qs.aggregate(total=Sum("amount_bdt"))["total"] or Decimal("0.00")
    return {
        "total_transactions": qs.count(),
        "credits_added": added_credits,
        "credits_spent": abs(spent_credits),
        "total_spend_usd": float(total_usd),
        "total_spend_bdt": float(total_bdt),
    }

