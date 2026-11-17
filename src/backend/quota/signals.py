"""Signals provisioning starter quota, profile, free plan, and initial ledger transaction."""

from __future__ import annotations

from django.conf import settings
from django.db import DatabaseError
from django.db.models.signals import post_save
from django.dispatch import receiver

from transactions.models import Transaction
from .models import UserQuota


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_initial_user_quota(sender, instance, created: bool, **kwargs) -> None:
    """Provision starter quota, welcome ledger entry, profile, and Starter Free plan."""
    if not created:
        return

    quota, q_created = UserQuota.objects.get_or_create(user=instance)
    if q_created and not Transaction.objects.filter(user=instance).exists():
        Transaction.objects.create(
            user=instance,
            tx_type=Transaction.TxType.BONUS,
            amount_usd=0,
            credits_delta=quota.total_credits,
            balance_after=quota.remaining_credits,
            description="Starter welcome credits",
        )

    try:
        from api.models import UserProfile
        from billing.models import Plan, Subscription

        UserProfile.objects.get_or_create(user=instance)
        free_plan = Plan.objects.filter(slug="free", is_active=True).first()
        if free_plan is not None and not Subscription.objects.filter(user=instance).exists():
            Subscription.objects.create(user=instance, plan=free_plan)
    except DatabaseError:
        # Guard against early migration / partial schema setup when optional tables are unavailable.
        pass
