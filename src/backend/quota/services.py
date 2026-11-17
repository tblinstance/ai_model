"""Atomic quota reservation, credit granting, pre-flight check, and daily rate-limit services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from billing.models import Subscription
from transactions.models import Transaction
from transactions.services import record_transaction
from .models import QuotaUsageLog, UserQuota


class InsufficientQuotaError(Exception):
    """Raised when a user lacks credits, is inactive/canceled, or exceeds daily limits."""


TIER_BASE_COSTS: dict[str, dict[str, int]] = {
    "flash": {"chat": 1, "code": 2, "images": 4, "video": 8, "audio": 2, "rag": 1},
    "pro": {"chat": 3, "code": 5, "images": 10, "video": 20, "audio": 5, "rag": 2},
    "advance": {"chat": 6, "code": 10, "images": 18, "video": 36, "audio": 10, "rag": 4},
}


def estimate_request_cost(tier: str, task: str | None) -> int:
    """Return expected baseline credit cost for a model tier and task mode."""
    return TIER_BASE_COSTS.get(tier or "flash", {}).get(task or "chat", 1)


def get_or_create_quota(user: AbstractBaseUser) -> UserQuota:
    """Fetch or lazily initialize a UserQuota record."""
    quota, _ = UserQuota.objects.get_or_create(user=user)
    return quota


def _reset_daily_counter_if_needed(quota: UserQuota, today: date | None = None) -> bool:
    """Reset the daily request counter when the calendar date advances."""
    current_date = today or timezone.localdate()
    if quota.last_reset_date != current_date:
        quota.daily_requests = 0
        quota.last_reset_date = current_date
        return True
    return False


def _validate_account_eligibility(user: AbstractBaseUser, quota: UserQuota, required_credits: int) -> None:
    """Ensure active user/subscription status, daily rate limit, and credit balance."""
    if not getattr(user, "is_active", True):
        raise InsufficientQuotaError("User account is inactive.")

    sub = Subscription.objects.filter(user=user).select_related("plan").first()
    if sub is not None and sub.status == Subscription.Status.CANCELED:
        raise InsufficientQuotaError("Subscription is canceled. Activate a billing plan to continue.")

    if quota.daily_requests >= quota.max_daily_requests:
        raise InsufficientQuotaError(
            f"Daily request limit ({quota.max_daily_requests}) reached. Upgrade plan or wait for reset."
        )

    if quota.remaining_credits < required_credits:
        raise InsufficientQuotaError(
            f"Insufficient credits: need {required_credits}, available {quota.remaining_credits}."
        )


def check_user_quota(user: AbstractBaseUser, required_credits: int = 1) -> UserQuota:
    """Run pre-flight account, subscription, daily limit, and balance verification."""
    quota = get_or_create_quota(user)
    if _reset_daily_counter_if_needed(quota):
        quota.save(update_fields=["daily_requests", "last_reset_date", "updated_at"])
    _validate_account_eligibility(user, quota, required_credits)
    return quota


@transaction.atomic
def grant_credits(
    *,
    user: AbstractBaseUser,
    credits: int,
    tx_type: str = Transaction.TxType.BONUS,
    amount_usd: Decimal | float | int = 0,
    amount_bdt: Decimal | float | int | None = None,
    currency: str = "USD",
    payment_method: str = "",
    tnxid: str = "",
    description: str = "",
    max_daily_requests: int | None = None,
    sync_daily_limit: bool = False,
    metadata: dict[str, object] | None = None,
) -> tuple[UserQuota, Transaction]:
    """Grant credits to a user and emit a corresponding transaction entry."""
    quota = get_or_create_quota(user)
    quota = UserQuota.objects.select_for_update().get(pk=quota.pk)
    quota.total_credits += credits
    if max_daily_requests is not None:
        quota.max_daily_requests = (
            max_daily_requests if sync_daily_limit else max(quota.max_daily_requests, max_daily_requests)
        )
    quota.save()

    tx = record_transaction(
        user=user,
        tx_type=tx_type,
        credits_delta=credits,
        balance_after=quota.remaining_credits,
        amount_usd=amount_usd,
        amount_bdt=amount_bdt,
        currency=currency,
        payment_method=payment_method,
        tnxid=tnxid,
        description=description or f"Granted {credits} credits",
        metadata=metadata,
    )
    return quota, tx


@transaction.atomic
def consume_user_quota(
    *,
    user: AbstractBaseUser,
    credits: int,
    model_tier: str,
    task_type: str,
    endpoint: str,
    latency_ms: float = 0.0,
) -> UserQuota:
    """Atomically deduct credits and increment daily usage counters."""
    quota = get_or_create_quota(user)
    quota = UserQuota.objects.select_for_update().get(pk=quota.pk)

    _reset_daily_counter_if_needed(quota)
    _validate_account_eligibility(user, quota, credits)

    quota.used_credits += credits
    quota.daily_requests += 1
    quota.save()

    QuotaUsageLog.objects.create(
        user=user,
        endpoint=endpoint,
        model_tier=model_tier,
        task_type=task_type,
        credits_consumed=credits,
        latency_ms=latency_ms,
    )

    record_transaction(
        user=user,
        tx_type=Transaction.TxType.USAGE_DEDUCTION,
        credits_delta=-credits,
        balance_after=quota.remaining_credits,
        model_tier=model_tier,
        task_type=task_type,
        description=f"{model_tier.upper()} {task_type} generation ({endpoint})",
    )
    return quota
