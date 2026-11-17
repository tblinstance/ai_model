"""Idempotent seed command initializing plans, starter agents, and a demo user."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from Agent.views import ensure_default_agents
from billing.models import Plan, Subscription
from billing.services import ensure_default_plans
from quota.services import get_or_create_quota


class Command(BaseCommand):
    """Seeds billing plans, public agents, and a demo user for quick startup."""

    help = "Seed default billing plans, AI agents, and a local demo account."

    def handle(self, *args, **options) -> None:
        plans = ensure_default_plans()
        ensure_default_agents()

        user_model = get_user_model()
        demo_user, created = user_model.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@ai-model.local"},
        )
        if created:
            demo_user.set_password("DemoPass123!")
            demo_user.save()

        quota = get_or_create_quota(demo_user)
        if quota.total_credits < 500:
            quota.total_credits = 500
            quota.save()

        free_plan = Plan.objects.filter(slug="free").first()
        if free_plan and not Subscription.objects.filter(user=demo_user).exists():
            Subscription.objects.create(user=demo_user, plan=free_plan)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(plans)} billing plans, default agents, and demo user (username=demo)."
            )
        )

