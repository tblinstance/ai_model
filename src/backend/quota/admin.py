"""Admin registrations for quota balances and logs."""

from django.contrib import admin

from api.verification import verify_user_account_state
from .models import QuotaUsageLog, UserQuota


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "total_credits", "used_credits", "remaining_credits", "daily_requests", "max_daily_requests")
    search_fields = ("user__username", "user__email")
    actions = ["verify_and_reconcile_quotas"]

    @admin.action(description="Verify & reconcile selected users' profile, billing, and balance")
    def verify_and_reconcile_quotas(self, request, queryset) -> None:
        count = 0
        for quota in queryset.select_related("user"):
            verify_user_account_state(quota.user, reconcile=True)
            count += 1
        self.message_user(request, f"Verified and reconciled balance ledger for {count} quota record(s).")


@admin.register(QuotaUsageLog)
class QuotaUsageLogAdmin(admin.ModelAdmin):
    list_display = ("user", "model_tier", "task_type", "credits_consumed", "latency_ms", "created_at")
    list_filter = ("model_tier", "task_type")
