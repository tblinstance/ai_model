"""Billing services for plan seeding and subscription transitions."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import hashlib
import hmac
import re
from typing import Any
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from quota.models import UserQuota
from quota.services import get_or_create_quota, grant_credits
from transactions.models import Transaction
from transactions.services import record_transaction
from .models import Invoice, MfsPaymentRequest, Plan, Subscription


CREDIT_PACK_UNIT_USD = Decimal("0.01")
BDT_PER_USD = Decimal("120.00")
MFS_PAYMENT_METHODS: dict[str, str] = {
    "bkash": "bKash",
    "nagad": "Nagad",
    "rocket": "Rocket",
    "upay": "Upay",
}
TNXID_PATTERN = re.compile(r"^[A-Z0-9_-]{6,64}$")


def compute_credit_pack_usd(credits: int) -> Decimal:
    """Compute authoritative USD price ($0.01/credit) for a credit pack purchase."""
    return (Decimal(credits) * CREDIT_PACK_UNIT_USD).quantize(Decimal("0.01"))


def usd_to_bdt(amount_usd: Decimal | float | int | str) -> Decimal:
    """Convert USD amount to authoritative BDT total using fixed 120.00 rate."""
    return (Decimal(str(amount_usd)) * BDT_PER_USD).quantize(Decimal("0.01"))


def compute_credit_pack_bdt(credits: int) -> Decimal:
    """Compute authoritative BDT price for a credit pack purchase."""
    return usd_to_bdt(compute_credit_pack_usd(credits))


def normalize_tnxid(tnxid: str | None) -> str:
    """Normalize a Bangladeshi MFS transaction ID (TrxID)."""
    return (tnxid or "").strip().upper()


class PlanAlreadyActiveError(Exception):
    """Raised when attempting to re-activate a subscription plan that is already active."""


class PaymentValidationError(Exception):
    """Raised when BDT totals, MFS method, or TrxID fail validation."""


def validate_mfs_payment(
    payment_method: str | None,
    tnxid: str | None,
    *,
    expected_usd: Decimal,
    currency: str | None = None,
    amount_bdt: Decimal | None = None,
    require_mfs: bool = False,
    exclude_request_id: int | None = None,
) -> dict[str, Any]:
    """Validate optional/MFS (bKash, Nagad, Rocket, Upay) payment details and TrxID uniqueness."""
    method = (payment_method or "").strip().lower()
    clean_tnxid = normalize_tnxid(tnxid)
    expected_bdt = usd_to_bdt(expected_usd)
    req_currency = (currency or ("BDT" if (method or clean_tnxid) else "USD")).strip().upper()

    if expected_bdt <= Decimal("0.00"):
        return {
            "currency": req_currency if req_currency in ("USD", "BDT") else "USD",
            "amount_bdt": Decimal("0.00"),
            "payment_method": "",
            "tnxid": "",
        }

    if amount_bdt is not None and Decimal(amount_bdt).quantize(Decimal("0.01")) != expected_bdt:
        raise PaymentValidationError(
            f"Checkout BDT mismatch: expected ৳{expected_bdt} BDT (got ৳{Decimal(amount_bdt).quantize(Decimal('0.01'))})."
        )

    if require_mfs or method or clean_tnxid:
        if method not in MFS_PAYMENT_METHODS:
            raise PaymentValidationError(
                "Unsupported payment method. Select bKash, Nagad, Rocket, or Upay."
            )
        if not clean_tnxid or not TNXID_PATTERN.match(clean_tnxid):
            raise PaymentValidationError(
                "Enter a valid TrxID (at least 6 alphanumeric characters) for your MFS payment."
            )
        req_qs = MfsPaymentRequest.objects.filter(tnxid=clean_tnxid)
        if exclude_request_id is not None:
            req_qs = req_qs.exclude(pk=exclude_request_id)
        if (
            Transaction.objects.filter(tnxid=clean_tnxid).exists()
            or Invoice.objects.filter(tnxid=clean_tnxid).exists()
            or req_qs.exists()
        ):
            raise PaymentValidationError(
                f"Transaction ID '{clean_tnxid}' has already been recorded."
            )
        req_currency = "BDT"

    return {
        "currency": req_currency if req_currency in ("USD", "BDT") else "BDT",
        "amount_bdt": expected_bdt,
        "payment_method": method,
        "tnxid": clean_tnxid,
    }


def sign_billing_event(*, user_id: int, reference: str, amount_usd: str, credits: int) -> str:
    """Sign billing invoices and top-up receipts using HMAC-SHA256 and BILLING_SECRET_KEY."""
    secret = getattr(settings, "BILLING_SECRET_KEY", settings.SECRET_KEY).encode("utf-8")
    payload = f"{user_id}:{reference}:{amount_usd}:{credits}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_billing_signature(*, user_id: int, reference: str, amount_usd: str, credits: int, signature: str) -> bool:
    """Constant-time verification for an HMAC-SHA256 billing receipt signature."""
    expected = sign_billing_event(
        user_id=user_id,
        reference=reference,
        amount_usd=amount_usd,
        credits=credits,
    )
    return hmac.compare_digest(expected, signature or "")

DEFAULT_PLANS = [
    {
        "slug": "free",
        "name": "Free",
        "monthly_price_usd": "0.00",
        "monthly_credits": 250,
        "daily_request_limit": 250,
        "allowed_tiers": ["flash", "pro"],
        "description": "Free tier with Flash and Pro access for prototyping.",
    },
    {
        "slug": "flash-studio",
        "name": "Plus",
        "monthly_price_usd": "19.00",
        "monthly_credits": 2500,
        "daily_request_limit": 1500,
        "allowed_tiers": ["flash", "pro"],
        "description": "High-throughput Flash tier tuned for fast chat, code, and images.",
    },
    {
        "slug": "pro-builder",
        "name": "Pro",
        "monthly_price_usd": "49.00",
        "monthly_credits": 8000,
        "daily_request_limit": 5000,
        "allowed_tiers": ["flash", "pro", "advance"],
        "description": "Balanced deep-reasoning tier across Chat, Images, Video, and Code.",
    },
    {
        "slug": "advance-enterprise",
        "name": "Enterprise",
        "monthly_price_usd": "129.00",
        "monthly_credits": 30000,
        "daily_request_limit": 20000,
        "allowed_tiers": ["flash", "pro", "advance"],
        "description": "Flagship synthesis tier with maximum monthly credits and daily quota.",
    },
]


def ensure_default_plans() -> list[Plan]:
    """Idempotently ensure default billing plans exist in the database."""
    plans: list[Plan] = []
    for item in DEFAULT_PLANS:
        plan, _ = Plan.objects.update_or_create(slug=item["slug"], defaults=item)
        plans.append(plan)
    return plans


def get_or_create_subscription(user: AbstractBaseUser) -> Subscription | None:
    """Return a user's subscription, provisioning the Free plan if missing."""
    if not Plan.objects.exists():
        ensure_default_plans()
    sub = Subscription.objects.filter(user=user).select_related("plan").first()
    if sub is None:
        free_plan = Plan.objects.filter(slug="free", is_active=True).first()
        if free_plan is None:
            return None
        sub = Subscription.objects.create(user=user, plan=free_plan)
    return sub


@transaction.atomic
def subscribe_user_to_plan(
    user: AbstractBaseUser,
    plan: Plan,
    *,
    payment_method: str = "",
    tnxid: str = "",
    currency: str | None = None,
    amount_bdt: Decimal | None = None,
    allow_same_plan: bool = False,
    skip_mfs_request_id: int | None = None,
) -> tuple[Subscription, Invoice]:
    """Activate or switch a user's plan, record BDT/MFS invoice, and grant credits atomically."""
    existing = Subscription.objects.select_for_update().filter(user=user).select_related("plan").first()
    if not allow_same_plan and existing is not None and existing.plan_id == plan.id and existing.status == Subscription.Status.ACTIVE:
        raise PlanAlreadyActiveError(f"'{plan.name}' is already your active plan.")

    payment = validate_mfs_payment(
        payment_method,
        tnxid,
        expected_usd=plan.monthly_price_usd,
        currency=currency,
        amount_bdt=amount_bdt,
        exclude_request_id=skip_mfs_request_id,
    )

    had_prior_credits = (
        existing is not None
        or Invoice.objects.filter(user=user).exists()
        or Transaction.objects.filter(user=user).exists()
    )
    renews_at = timezone.now() + timedelta(days=30)
    subscription, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "status": Subscription.Status.ACTIVE,
            "started_at": timezone.now(),
            "renews_at": renews_at,
            "auto_renew": True,
        },
    )

    # Downgrading back to a $0 free plan syncs daily limits without re-granting free starter credits.
    grant_amount = 0 if (plan.monthly_price_usd <= 0 and had_prior_credits) else plan.monthly_credits

    invoice = Invoice.objects.create(
        user=user,
        plan=plan,
        currency=payment["currency"],
        amount_usd=plan.monthly_price_usd,
        amount_bdt=payment["amount_bdt"],
        payment_method=payment["payment_method"],
        tnxid=payment["tnxid"],
        credits_granted=grant_amount,
        status="paid",
    )

    if grant_amount > 0:
        signature = sign_billing_event(
            user_id=user.id,
            reference=invoice.invoice_number,
            amount_usd=str(plan.monthly_price_usd),
            credits=grant_amount,
        )
        method_label = MFS_PAYMENT_METHODS.get(payment["payment_method"], "")
        via_suffix = f" via {method_label} ({payment['tnxid']})" if method_label and payment["tnxid"] else ""
        grant_credits(
            user=user,
            credits=grant_amount,
            tx_type=Transaction.TxType.SUBSCRIPTION,
            amount_usd=plan.monthly_price_usd,
            amount_bdt=payment["amount_bdt"],
            currency=payment["currency"],
            payment_method=payment["payment_method"],
            tnxid=payment["tnxid"],
            description=f"Activated {plan.name} ({invoice.invoice_number}){via_suffix}",
            max_daily_requests=plan.daily_request_limit,
            sync_daily_limit=True,
            metadata={
                "invoice_number": invoice.invoice_number,
                "receipt_signature": signature,
                "payment_method": payment["payment_method"],
                "tnxid": payment["tnxid"],
                "amount_bdt": str(payment["amount_bdt"]),
                "currency": payment["currency"],
            },
        )
    else:
        quota = get_or_create_quota(user)
        quota = UserQuota.objects.select_for_update().get(pk=quota.pk)
        if quota.max_daily_requests != plan.daily_request_limit:
            quota.max_daily_requests = plan.daily_request_limit
            quota.save(update_fields=["max_daily_requests", "updated_at"])
    return subscription, invoice


def verify_transaction_receipt(tx: Transaction) -> dict[str, Any]:
    """Verify pricing parity, invoice linkage, and HMAC receipt signature for a checkout transaction."""
    metadata = tx.metadata or {}
    signature = str(metadata.get("receipt_signature") or "")
    has_signature = bool(signature)

    price_valid = True
    invoice_valid = True
    signature_valid = True

    if tx.tx_type == Transaction.TxType.CREDIT_PURCHASE:
        expected_usd = compute_credit_pack_usd(tx.credits_delta)
        usd_ok = Decimal(tx.amount_usd).quantize(Decimal("0.01")) == expected_usd
        bdt_ok = (
            Decimal(tx.amount_bdt).quantize(Decimal("0.01")) == Decimal("0.00")
            or Decimal(tx.amount_bdt).quantize(Decimal("0.01")) == usd_to_bdt(expected_usd)
        )
        price_valid = bool(usd_ok and bdt_ok)
        reference = str(metadata.get("reference_tag") or f"topup-{tx.user_id}-{tx.credits_delta}")
        if has_signature:
            signature_valid = verify_billing_signature(
                user_id=tx.user_id,
                reference=reference,
                amount_usd=str(Decimal(tx.amount_usd).quantize(Decimal("0.01"))),
                credits=tx.credits_delta,
                signature=signature,
            )
    elif tx.tx_type == Transaction.TxType.SUBSCRIPTION:
        inv_num = str(metadata.get("invoice_number") or "")
        if inv_num:
            inv = Invoice.objects.filter(user_id=tx.user_id, invoice_number=inv_num).first()
            invoice_valid = bool(
                inv is not None
                and inv.credits_granted == tx.credits_delta
                and Decimal(inv.amount_usd).quantize(Decimal("0.01"))
                == Decimal(tx.amount_usd).quantize(Decimal("0.01"))
            )
        if has_signature:
            signature_valid = bool(
                inv_num
                and verify_billing_signature(
                    user_id=tx.user_id,
                    reference=inv_num,
                    amount_usd=str(Decimal(tx.amount_usd).quantize(Decimal("0.01"))),
                    credits=tx.credits_delta,
                    signature=signature,
                )
            )

    return {
        "has_signature": has_signature,
        "signature_valid": signature_valid,
        "price_valid": price_valid,
        "invoice_valid": invoice_valid,
        "valid": bool(signature_valid and price_valid and invoice_valid),
    }


def _finalize_receipt_verification(
    *,
    reference: str,
    amount_usd: Decimal,
    credits_granted: int,
    sig_valid: bool,
    price_valid: bool,
    invoice_valid: bool,
    balance_verified: bool,
    current_balance: int,
    issues: list[str],
) -> dict[str, Any]:
    """Assemble standardized checkout receipt verification report and append detected issues."""
    if not sig_valid:
        issues.append("invalid_checkout_signature")
    if not price_valid:
        issues.append("checkout_price_mismatch")
    if not invoice_valid:
        issues.append("invoice_ledger_mismatch")

    receipt_ok = bool(sig_valid and price_valid and invoice_valid)
    return {
        "verified": bool(receipt_ok and balance_verified),
        "mode": "receipt",
        "reference": reference,
        "signature_valid": sig_valid,
        "price_valid": price_valid,
        "invoice_valid": invoice_valid,
        "balance_verified": balance_verified,
        "amount_usd": str(Decimal(amount_usd).quantize(Decimal("0.01"))),
        "credits_granted": credits_granted,
        "remaining_credits": current_balance,
        "issues": issues,
    }


def _verify_checkout_receipt_ref(
    user: AbstractBaseUser,
    *,
    reference: str,
    balance_verified: bool,
    current_balance: int,
    issues: list[str],
) -> dict[str, Any]:
    """Verify an invoice number (INV-...) or transaction reference_id (tx_...) against HMAC and ledger."""
    invoice = Invoice.objects.filter(user=user, invoice_number=reference).select_related("plan").first()
    if invoice is not None:
        linked_tx = (
            Transaction.objects.filter(
                user=user,
                tx_type=Transaction.TxType.SUBSCRIPTION,
                metadata__invoice_number=invoice.invoice_number,
            )
            .order_by("-created_at")
            .first()
        )
        if invoice.credits_granted == 0 and linked_tx is None:
            zero_ok = Decimal(invoice.amount_usd).quantize(Decimal("0.01")) == Decimal("0.00")
            return _finalize_receipt_verification(
                reference=invoice.invoice_number,
                amount_usd=invoice.amount_usd,
                credits_granted=invoice.credits_granted,
                sig_valid=zero_ok,
                price_valid=zero_ok,
                invoice_valid=True,
                balance_verified=balance_verified,
                current_balance=current_balance,
                issues=issues,
            )
        if linked_tx is not None:
            tx_check = verify_transaction_receipt(linked_tx)
            return _finalize_receipt_verification(
                reference=invoice.invoice_number,
                amount_usd=invoice.amount_usd,
                credits_granted=invoice.credits_granted,
                sig_valid=bool(tx_check["has_signature"] and tx_check["signature_valid"]),
                price_valid=tx_check["price_valid"],
                invoice_valid=tx_check["invoice_valid"],
                balance_verified=balance_verified,
                current_balance=current_balance,
                issues=issues,
            )
        return _finalize_receipt_verification(
            reference=invoice.invoice_number,
            amount_usd=invoice.amount_usd,
            credits_granted=invoice.credits_granted,
            sig_valid=False,
            price_valid=False,
            invoice_valid=False,
            balance_verified=balance_verified,
            current_balance=current_balance,
            issues=issues,
        )

    tx = Transaction.objects.filter(user=user, reference_id=reference).first()
    if tx is None:
        raise Invoice.DoesNotExist(f"Checkout receipt '{reference}' not found.")

    tx_check = verify_transaction_receipt(tx)
    return _finalize_receipt_verification(
        reference=tx.reference_id,
        amount_usd=tx.amount_usd,
        credits_granted=tx.credits_delta,
        sig_valid=bool(tx_check["has_signature"] and tx_check["signature_valid"]),
        price_valid=tx_check["price_valid"],
        invoice_valid=tx_check["invoice_valid"],
        balance_verified=balance_verified,
        current_balance=current_balance,
        issues=issues,
    )


def verify_checkout_request(
    user: AbstractBaseUser,
    *,
    mode: str,
    credits: int | None = None,
    amount_usd: Decimal | None = None,
    amount_bdt: Decimal | None = None,
    payment_method: str | None = None,
    tnxid: str | None = None,
    plan_slug: str | None = None,
    reference: str | None = None,
) -> dict[str, Any]:
    """Verify pre-checkout eligibility/BDT totals/MFS TrxID or verify an existing receipt."""
    from api.verification import verify_user_account_state

    account_report = verify_user_account_state(user, reconcile=False)
    bal = account_report["balance"]
    current_balance = int(bal["remaining_credits"])
    balance_verified = bool(bal["verified"])
    issues = list(account_report["issues"])

    if mode == "credits":
        credit_qty = int(credits or 0)
        expected_usd = compute_credit_pack_usd(credit_qty)
        expected_bdt = usd_to_bdt(expected_usd)
        price_matches = True
        if amount_usd is not None:
            price_matches = Decimal(amount_usd).quantize(Decimal("0.01")) == expected_usd
        if amount_bdt is not None and Decimal(amount_bdt).quantize(Decimal("0.01")) != expected_bdt:
            price_matches = False
        if not price_matches:
            issues.append("checkout_price_mismatch")

        mfs_ok = True
        clean_method = (payment_method or "").strip().lower()
        clean_tnxid = normalize_tnxid(tnxid)
        if clean_method or clean_tnxid:
            try:
                validate_mfs_payment(
                    clean_method,
                    clean_tnxid,
                    expected_usd=expected_usd,
                    currency="BDT",
                    amount_bdt=amount_bdt,
                )
            except PaymentValidationError:
                mfs_ok = False
                issues.append("invalid_mfs_payment")

        eligible = bool(getattr(user, "is_active", True) and price_matches and mfs_ok)

        return {
            "verified": bool(balance_verified and eligible),
            "eligible": eligible,
            "mode": "credits",
            "credits_granted": credit_qty,
            "amount_usd": str(expected_usd),
            "amount_bdt": str(expected_bdt),
            "bdt_rate": str(BDT_PER_USD),
            "payment_method": clean_method,
            "tnxid": clean_tnxid,
            "current_balance": current_balance,
            "projected_balance": current_balance + (credit_qty if eligible else 0),
            "balance_verified": balance_verified,
            "issues": issues,
        }

    if mode == "plan":
        plan = Plan.objects.get(slug=plan_slug, is_active=True)
        existing = Subscription.objects.filter(user=user).select_related("plan").first()
        already_active = bool(
            existing is not None and existing.plan_id == plan.id and existing.status == Subscription.Status.ACTIVE
        )
        if already_active:
            issues.append("plan_already_active")

        had_prior_credits = (
            existing is not None
            or Invoice.objects.filter(user=user).exists()
            or Transaction.objects.filter(user=user).exists()
        )
        grant_amount = 0 if (plan.monthly_price_usd <= 0 and had_prior_credits) else plan.monthly_credits
        expected_bdt = usd_to_bdt(plan.monthly_price_usd)
        eligible = bool(getattr(user, "is_active", True) and not already_active)
        return {
            "verified": bool(balance_verified and eligible),
            "eligible": eligible,
            "mode": "plan",
            "plan_slug": plan.slug,
            "plan_name": plan.name,
            "amount_usd": str(Decimal(plan.monthly_price_usd).quantize(Decimal("0.01"))),
            "amount_bdt": str(expected_bdt),
            "bdt_rate": str(BDT_PER_USD),
            "credits_granted": grant_amount,
            "daily_request_limit": plan.daily_request_limit,
            "allowed_tiers": plan.allowed_tiers,
            "current_balance": current_balance,
            "projected_balance": current_balance + (grant_amount if eligible else 0),
            "balance_verified": balance_verified,
            "issues": issues,
        }

    return _verify_checkout_receipt_ref(
        user,
        reference=(reference or "").strip(),
        balance_verified=balance_verified,
        current_balance=current_balance,
        issues=issues,
    )


def create_mfs_payment_request(
    user: AbstractBaseUser,
    *,
    kind: str,
    payment_method: str,
    tnxid: str,
    credits: int = 0,
    plan: Plan | None = None,
    amount_bdt: Decimal | None = None,
    sender_number: str = "",
) -> MfsPaymentRequest:
    """Create a pending BDT MFS checkout request for Admin review & approval."""
    if kind == MfsPaymentRequest.Kind.CREDITS:
        if credits < 10 or credits > 100000:
            raise PaymentValidationError("Credit pack purchases must be between 10 and 100,000 credits.")
        expected_usd = compute_credit_pack_usd(credits)
        credits_requested = credits
        target_plan = None
    elif kind == MfsPaymentRequest.Kind.PLAN:
        if plan is None:
            raise PaymentValidationError("A valid active billing plan is required.")
        if plan.monthly_price_usd <= Decimal("0.00"):
            raise PaymentValidationError("Free tier switches do not require an MFS TrxID.")
        existing = Subscription.objects.filter(user=user).select_related("plan").first()
        if existing is not None and existing.plan_id == plan.id and existing.status == Subscription.Status.ACTIVE:
            raise PlanAlreadyActiveError(f"'{plan.name}' is already your active plan.")
        expected_usd = Decimal(plan.monthly_price_usd).quantize(Decimal("0.01"))
        credits_requested = plan.monthly_credits
        target_plan = plan
    else:
        raise PaymentValidationError(f"Unsupported checkout request kind '{kind}'.")

    payment = validate_mfs_payment(
        payment_method,
        tnxid,
        expected_usd=expected_usd,
        currency="BDT",
        amount_bdt=amount_bdt,
        require_mfs=True,
    )
    return MfsPaymentRequest.objects.create(
        user=user,
        kind=kind,
        plan=target_plan,
        credits_requested=credits_requested,
        currency="BDT",
        amount_usd=expected_usd,
        amount_bdt=payment["amount_bdt"],
        payment_method=payment["payment_method"],
        tnxid=payment["tnxid"],
        sender_number=(sender_number or "").strip(),
        status=MfsPaymentRequest.Status.PENDING,
    )


@transaction.atomic
def approve_mfs_payment_request(
    request_id: int,
    *,
    admin_user: AbstractBaseUser,
    admin_note: str = "",
) -> MfsPaymentRequest:
    """Verify & approve a pending MFS request, crediting quota and activating plan atomically."""
    req = MfsPaymentRequest.objects.select_for_update().get(pk=request_id)
    if req.status != MfsPaymentRequest.Status.PENDING:
        raise PaymentValidationError(f"Payment request #{req.pk} is already {req.status}.")

    method_label = MFS_PAYMENT_METHODS.get(req.payment_method, req.payment_method)
    if req.kind == MfsPaymentRequest.Kind.CREDITS:
        reference_tag = f"topup-{req.user_id}-{req.credits_requested}"
        signature = sign_billing_event(
            user_id=req.user_id,
            reference=reference_tag,
            amount_usd=str(req.amount_usd),
            credits=req.credits_requested,
        )
        _, tx = grant_credits(
            user=req.user,
            credits=req.credits_requested,
            tx_type=Transaction.TxType.CREDIT_PURCHASE,
            amount_usd=req.amount_usd,
            amount_bdt=req.amount_bdt,
            currency="BDT",
            payment_method=req.payment_method,
            tnxid=req.tnxid,
            description=f"Approved {req.credits_requested} AI credits via {method_label} ({req.tnxid})",
            metadata={
                "receipt_signature": signature,
                "payment_method": req.payment_method,
                "tnxid": req.tnxid,
                "amount_bdt": str(req.amount_bdt),
                "currency": "BDT",
                "mfs_request_id": req.pk,
                "approved_by": getattr(admin_user, "username", ""),
            },
        )
        req.transaction = tx
    else:
        _, invoice = subscribe_user_to_plan(
            req.user,
            req.plan,
            payment_method=req.payment_method,
            tnxid=req.tnxid,
            currency="BDT",
            amount_bdt=req.amount_bdt,
            allow_same_plan=True,
            skip_mfs_request_id=req.pk,
        )
        req.invoice = invoice
        req.transaction = (
            Transaction.objects.filter(
                user=req.user,
                tx_type=Transaction.TxType.SUBSCRIPTION,
                metadata__invoice_number=invoice.invoice_number,
            )
            .order_by("-created_at")
            .first()
        )

    req.status = MfsPaymentRequest.Status.APPROVED
    req.reviewed_by = admin_user
    req.reviewed_at = timezone.now()
    req.admin_note = (admin_note or "").strip() or "Approved by admin"
    req.save()
    return req


@transaction.atomic
def reject_mfs_payment_request(
    request_id: int,
    *,
    admin_user: AbstractBaseUser,
    admin_note: str = "",
) -> MfsPaymentRequest:
    """Reject a pending MFS payment request without mutating user credits or billing."""
    req = MfsPaymentRequest.objects.select_for_update().get(pk=request_id)
    if req.status != MfsPaymentRequest.Status.PENDING:
        raise PaymentValidationError(f"Payment request #{req.pk} is already {req.status}.")

    req.status = MfsPaymentRequest.Status.REJECTED
    req.reviewed_by = admin_user
    req.reviewed_at = timezone.now()
    req.admin_note = (admin_note or "").strip() or "Rejected after TrxID verification"
    req.save()
    return req


def admin_grant_member_credits(
    target_user: AbstractBaseUser,
    *,
    credits: int,
    admin_user: AbstractBaseUser,
    description: str = "",
) -> tuple[UserQuota, Transaction]:
    """Admin-initiated credit grant recorded directly onto the member's ledger."""
    admin_name = getattr(admin_user, "username", "admin")
    note = (description or "").strip() or f"Admin credit grant by @{admin_name}"
    return grant_credits(
        user=target_user,
        credits=credits,
        tx_type=Transaction.TxType.BONUS,
        amount_usd=Decimal("0.00"),
        amount_bdt=Decimal("0.00"),
        currency="BDT",
        payment_method=Transaction.PaymentMethod.SYSTEM,
        description=note,
        metadata={"admin_grant": True, "granted_by": admin_name},
    )


@transaction.atomic
def admin_clear_member_balance(
    target_user: AbstractBaseUser,
    *,
    admin_user: AbstractBaseUser,
    description: str = "",
) -> tuple[UserQuota, Transaction | None, int]:
    """Clear a user's credit balance to 0 while keeping their transaction ledger balanced."""
    quota = get_or_create_quota(target_user)
    quota = UserQuota.objects.select_for_update().get(pk=quota.pk)
    previous_balance = int(quota.remaining_credits)
    ledger_net = int(Transaction.objects.filter(user=target_user).aggregate(s=Sum("credits_delta"))["s"] or 0)

    if previous_balance == 0 and quota.total_credits == 0 and quota.used_credits == 0 and ledger_net == 0:
        return quota, None, 0

    quota.total_credits = 0
    quota.used_credits = 0
    quota.save()

    tx: Transaction | None = None
    if ledger_net != 0:
        admin_name = getattr(admin_user, "username", "admin")
        note = (description or "").strip() or f"Balance cleared by admin @{admin_name}"
        tx = record_transaction(
            user=target_user,
            tx_type=Transaction.TxType.USAGE_DEDUCTION,
            credits_delta=-ledger_net,
            balance_after=0,
            amount_usd=Decimal("0.00"),
            amount_bdt=Decimal("0.00"),
            currency="BDT",
            payment_method=Transaction.PaymentMethod.SYSTEM,
            description=note,
            metadata={
                "admin_clear": True,
                "cleared_by": admin_name,
                "previous_balance": previous_balance,
                "previous_ledger_sum": ledger_net,
            },
        )
    return quota, tx, previous_balance



