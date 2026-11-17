"""Django management command to verify and optionally reconcile profile, billing, and balances."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.verification import verify_all_user_accounts, verify_user_account_state


class Command(BaseCommand):
    """Audit and reconcile UserProfile, Subscription/Plan, UserQuota, and Transaction ledger."""

    help = "Verify profile, billing subscription, quota balance, and transaction ledger consistency."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--username",
            type=str,
            default="",
            help="Optional username to verify; defaults to all registered users.",
        )
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="Repair missing profiles/subscriptions, sync daily limits, and balance ledger deltas.",
        )

    def handle(self, *args, **options) -> None:
        reconcile = bool(options.get("reconcile"))
        username = (options.get("username") or "").strip()

        if username:
            user = get_user_model().objects.get(username=username)
            reports = [verify_user_account_state(user, reconcile=reconcile)]
        else:
            reports = verify_all_user_accounts(reconcile=reconcile)

        all_ok = True
        for report in reports:
            uname = report["profile"]["username"]
            status_label = "VERIFIED" if report["verified"] else "ISSUES"
            bal = report["balance"]
            bil = report["billing"]
            chk = report["checkout"]
            chk_label = "OK" if chk["verified"] else "ISSUES"
            msg = (
                f"[{status_label}] @{uname} | plan={bil['plan_slug']} ({bil['subscription_status']}) | "
                f"balance={bal['remaining_credits']}/{bal['total_credits']} (ledger={bal['ledger_net_credits']}, "
                f"daily={bal['daily_requests']}/{bal['max_daily_requests']}) | "
                f"checkout={chk_label} (signed={chk['verified_signatures']}/{chk['signed_receipts']})"
            )
            if report["issues"]:
                all_ok = False
                msg += f" | issues={','.join(report['issues'])}"
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(self.style.SUCCESS(msg))

        if not reports:
            self.stdout.write("No users found.")
        elif all_ok:
            self.stdout.write(self.style.SUCCESS(f"All {len(reports)} account(s) verified cleanly."))

