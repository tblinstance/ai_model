"""Account verification and reconciliation for UserProfile, billing subscription, and balance ledger."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from api.models import UserProfile
from billing.models import Invoice, MfsPaymentRequest, Plan, Subscription
from billing.services import (
    ensure_default_plans,
    get_or_create_subscription,
    usd_to_bdt,
    verify_transaction_receipt,
)
from quota.models import QuotaUsageLog, UserQuota
from quota.services import _reset_daily_counter_if_needed, get_or_create_quota
from transactions.models import Transaction
from transactions.services import record_transaction


def _resolve_plan_for_subscription_tx(tx: Transaction, fallback_sub: Subscription | None) -> Plan | None:
    """Resolve the Plan corresponding to a subscription Transaction."""
    plan = Plan.objects.filter(
        monthly_credits=tx.credits_delta,
        monthly_price_usd=Decimal(tx.amount_usd).quantize(Decimal("0.01")),
    ).first()
    if plan is not None:
        return plan
    desc = (tx.description or "").lower()
    for candidate in Plan.objects.all():
        if candidate.name.lower() in desc or candidate.slug.lower() in desc:
            return candidate
    if fallback_sub is not None:
        return fallback_sub.plan
    return Plan.objects.filter(is_active=True).first()


def _reconcile_missing_subscription_invoices(user: AbstractBaseUser, sub: Subscription | None) -> int:
    """Backfill Invoice rows missing for verified SUBSCRIPTION transactions."""
    created_count = 0
    sub_txs = Transaction.objects.filter(
        user=user,
        tx_type=Transaction.TxType.SUBSCRIPTION,
        credits_delta__gte=0,
    ).order_by("created_at")

    for tx in sub_txs:
        metadata = tx.metadata or {}
        inv_num = str(metadata.get("invoice_number") or "").strip()
        if not inv_num:
            continue
        if Invoice.objects.filter(invoice_number=inv_num).exists():
            continue

        check = verify_transaction_receipt(tx)
        if not check["signature_valid"] or not check["price_valid"]:
            continue

        plan = _resolve_plan_for_subscription_tx(tx, sub)
        if plan is None:
            continue

        raw_tnxid = str(tx.tnxid or metadata.get("tnxid") or "").strip().upper()
        safe_tnxid = raw_tnxid if (raw_tnxid and not Invoice.objects.filter(tnxid=raw_tnxid).exists()) else ""
        method = str(tx.payment_method or metadata.get("payment_method") or "").strip().lower()
        amount_usd = Decimal(tx.amount_usd).quantize(Decimal("0.01"))
        tx_bdt = Decimal(tx.amount_bdt or 0).quantize(Decimal("0.01"))
        amount_bdt = tx_bdt if tx_bdt > Decimal("0.00") else usd_to_bdt(amount_usd)
        currency = str(tx.currency or metadata.get("currency") or ("BDT" if safe_tnxid else "USD")).strip().upper() or "USD"

        inv = Invoice.objects.create(
            user=user,
            plan=plan,
            invoice_number=inv_num,
            currency=currency,
            amount_usd=amount_usd,
            amount_bdt=amount_bdt,
            payment_method=method,
            tnxid=safe_tnxid,
            credits_granted=tx.credits_delta,
            status="paid",
        )
        MfsPaymentRequest.objects.filter(transaction=tx, invoice__isnull=True).update(invoice=inv)
        created_count += 1

    return created_count


def verify_user_account_state(user: AbstractBaseUser, *, reconcile: bool = False) -> dict[str, Any]:
    """Audit user profile, billing subscription, quota math, and transaction ledger parity."""
    if reconcile:
        return _verify_locked(user, reconcile=True)
    return _build_verification_report(user, reconciled=False)


@transaction.atomic
def _verify_locked(user: AbstractBaseUser, *, reconcile: bool) -> dict[str, Any]:
    ensure_default_plans()
    UserProfile.objects.get_or_create(user=user)
    sub = get_or_create_subscription(user)

    quota = get_or_create_quota(user)
    quota = UserQuota.objects.select_for_update().get(pk=quota.pk)
    quota_changed = _reset_daily_counter_if_needed(quota)

    if sub is not None and quota.max_daily_requests != sub.plan.daily_request_limit:
        quota.max_daily_requests = sub.plan.daily_request_limit
        quota_changed = True

    if quota.total_credits < quota.used_credits:
        quota.total_credits = quota.used_credits
        quota_changed = True

    if quota_changed:
        quota.save()

    ledger_net = int(Transaction.objects.filter(user=user).aggregate(s=Sum("credits_delta"))["s"] or 0)
    discrepancy = quota.remaining_credits - ledger_net
    if discrepancy != 0:
        record_transaction(
            user=user,
            tx_type=Transaction.TxType.BONUS if discrepancy > 0 else Transaction.TxType.USAGE_DEDUCTION,
            credits_delta=discrepancy,
            balance_after=quota.remaining_credits,
            description="Verified balance ledger reconciliation",
            metadata={"reconciled": True, "previous_ledger_sum": ledger_net},
        )

    _reconcile_missing_subscription_invoices(user, sub)

    return _build_verification_report(user, reconciled=reconcile)


def _build_verification_report(user: AbstractBaseUser, *, reconciled: bool) -> dict[str, Any]:
    profile = UserProfile.objects.filter(user=user).first()
    sub = Subscription.objects.filter(user=user).select_related("plan").first()
    quota = get_or_create_quota(user)

    tx_qs = Transaction.objects.filter(user=user)
    tx_count = tx_qs.count()
    ledger_net = int(tx_qs.aggregate(s=Sum("credits_delta"))["s"] or 0)
    usage_logs_credits = int(
        QuotaUsageLog.objects.filter(user=user).aggregate(s=Sum("credits_consumed"))["s"] or 0
    )
    inv_agg = Invoice.objects.filter(user=user).aggregate(
        credits=Sum("credits_granted"),
    )
    invoices_count = Invoice.objects.filter(user=user).count()
    invoices_total_credits = int(inv_agg["credits"] or 0)

    checkout_txs = list(
        tx_qs.filter(
            tx_type__in=[Transaction.TxType.CREDIT_PURCHASE, Transaction.TxType.SUBSCRIPTION]
        )
    )
    signed_receipts = 0
    verified_signatures = 0
    unsigned_legacy = 0
    invalid_signatures = 0
    price_mismatches = 0
    invoice_mismatches = 0
    total_spend_usd = 0.0
    total_spend_bdt = 0.0
    mfs_transactions = 0
    total_purchased_credits = 0

    for tx in checkout_txs:
        total_spend_usd += float(tx.amount_usd or 0)
        total_spend_bdt += float(tx.amount_bdt or 0)
        if tx.payment_method and tx.tnxid:
            mfs_transactions += 1
        total_purchased_credits += int(tx.credits_delta or 0)
        check = verify_transaction_receipt(tx)
        if check["has_signature"]:
            signed_receipts += 1
            if check["signature_valid"]:
                verified_signatures += 1
            else:
                invalid_signatures += 1
        else:
            unsigned_legacy += 1
        if not check["price_valid"]:
            price_mismatches += 1
        if not check["invoice_valid"]:
            invoice_mismatches += 1

    has_email = bool(user.email and "@" in user.email)
    profile_exists = profile is not None
    profile_verified = bool(user.is_active and profile_exists and has_email)

    has_sub = sub is not None
    sub_active = bool(sub is not None and sub.status == Subscription.Status.ACTIVE)
    daily_limit_synced = bool(sub is not None and quota.max_daily_requests == sub.plan.daily_request_limit)
    billing_verified = bool(has_sub and sub_active and daily_limit_synced)

    expected_remaining = max(0, quota.total_credits - quota.used_credits)
    quota_math_valid = bool(
        quota.total_credits >= quota.used_credits and quota.remaining_credits == expected_remaining
    )
    ledger_discrepancy = quota.remaining_credits - ledger_net
    ledger_balanced = ledger_discrepancy == 0
    daily_limit_ok = quota.daily_requests < quota.max_daily_requests
    balance_verified = bool(quota_math_valid and ledger_balanced and daily_limit_ok)
    checkout_verified = bool(
        invalid_signatures == 0
        and price_mismatches == 0
        and invoice_mismatches == 0
        and quota_math_valid
        and ledger_balanced
    )

    issues: list[str] = []
    if not user.is_active:
        issues.append("inactive_user")
    if not profile_exists:
        issues.append("missing_profile")
    if not has_email:
        issues.append("missing_email")
    if not has_sub:
        issues.append("missing_subscription")
    elif not sub_active:
        issues.append(f"subscription_{sub.status}")
    if has_sub and not daily_limit_synced:
        issues.append("daily_limit_out_of_sync")
    if not quota_math_valid:
        issues.append("quota_math_invalid")
    if not ledger_balanced:
        issues.append("ledger_mismatch")
    if not daily_limit_ok:
        issues.append("daily_limit_reached")
    if invalid_signatures > 0:
        issues.append("invalid_checkout_signature")
    if price_mismatches > 0:
        issues.append("checkout_price_mismatch")
    if invoice_mismatches > 0:
        issues.append("invoice_ledger_mismatch")

    return {
        "verified": bool(profile_verified and billing_verified and balance_verified and checkout_verified),
        "checked_at": timezone.now(),
        "reconciled": reconciled,
        "issues": issues,
        "profile": {
            "verified": profile_verified,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "has_email": has_email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "profile_exists": profile_exists,
            "display_name": profile.display_name if profile else "",
            "default_tier": profile.default_tier if profile else "flash",
            "default_task": profile.default_task if profile else "chat",
        },
        "billing": {
            "verified": billing_verified,
            "has_subscription": has_sub,
            "plan_slug": sub.plan.slug if sub else None,
            "plan_name": sub.plan.name if sub else "None",
            "subscription_status": sub.status if sub else "missing",
            "monthly_price_usd": float(sub.plan.monthly_price_usd) if sub else 0.0,
            "monthly_credits": sub.plan.monthly_credits if sub else 0,
            "daily_request_limit": sub.plan.daily_request_limit if sub else 0,
            "daily_limit_synced": daily_limit_synced,
            "allowed_tiers": sub.plan.allowed_tiers if sub else [],
            "invoices_count": invoices_count,
            "invoices_total_credits": invoices_total_credits,
        },
        "balance": {
            "verified": balance_verified,
            "total_credits": quota.total_credits,
            "used_credits": quota.used_credits,
            "remaining_credits": quota.remaining_credits,
            "quota_math_valid": quota_math_valid,
            "ledger_net_credits": ledger_net,
            "ledger_discrepancy": ledger_discrepancy,
            "ledger_balanced": ledger_balanced,
            "transaction_count": tx_count,
            "usage_logs_credits": usage_logs_credits,
            "usage_log_gap": quota.used_credits - usage_logs_credits,
            "daily_requests": quota.daily_requests,
            "max_daily_requests": quota.max_daily_requests,
            "daily_limit_ok": daily_limit_ok,
        },
        "checkout": {
            "verified": checkout_verified,
            "checkout_transactions": len(checkout_txs),
            "signed_receipts": signed_receipts,
            "verified_signatures": verified_signatures,
            "unsigned_legacy": unsigned_legacy,
            "invalid_signatures": invalid_signatures,
            "price_mismatches": price_mismatches,
            "invoice_mismatches": invoice_mismatches,
            "invoices_count": invoices_count,
            "invoices_total_credits": invoices_total_credits,
            "total_purchased_credits": total_purchased_credits,
            "total_spend_usd": round(total_spend_usd, 2),
            "total_spend_bdt": round(total_spend_bdt, 2),
            "mfs_transactions": mfs_transactions,
        },
    }


def verify_all_user_accounts(*, reconcile: bool = False) -> list[dict[str, Any]]:
    """Verify profile, billing, and balance state across all registered users."""
    User = get_user_model()
    return [verify_user_account_state(u, reconcile=reconcile) for u in User.objects.order_by("id")]

