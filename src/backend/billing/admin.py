"""Admin registrations for billing models with subscription-quota synchronization."""

from django.contrib import admin

from api.verification import verify_user_account_state
from .models import Invoice, MfsPaymentRequest, Plan, Subscription
from .services import (
    PaymentValidationError,
    PlanAlreadyActiveError,
    approve_mfs_payment_request,
    reject_mfs_payment_request,
    subscribe_user_to_plan,
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "monthly_price_usd", "monthly_credits", "daily_request_limit", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "started_at", "renews_at", "auto_renew")
    list_filter = ("status", "plan")
    actions = ["reconcile_subscription_balances"]

    def save_model(self, request, obj: Subscription, form, change: bool) -> None:
        """Grant credits and emit invoice/transaction when admin assigns or switches plan."""
        plan_changed = change and "plan" in form.changed_data
        new_non_free = not change and obj.plan.slug != "free"
        if plan_changed or new_non_free:
            synced_sub, _ = subscribe_user_to_plan(obj.user, obj.plan)
            obj.pk = synced_sub.pk
            return
        super().save_model(request, obj, form, change)
        verify_user_account_state(obj.user, reconcile=True)

    @admin.action(description="Verify & reconcile selected users' billing and balance")
    def reconcile_subscription_balances(self, request, queryset) -> None:
        count = 0
        for sub in queryset.select_related("user"):
            verify_user_account_state(sub.user, reconcile=True)
            count += 1
        self.message_user(request, f"Verified and reconciled billing/balance for {count} user(s).")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "user",
        "plan",
        "payment_method",
        "tnxid",
        "amount_bdt",
        "amount_usd",
        "credits_granted",
        "status",
        "created_at",
    )
    list_filter = ("currency", "payment_method", "status")
    search_fields = ("invoice_number", "tnxid", "user__username")


@admin.register(MfsPaymentRequest)
class MfsPaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "kind",
        "plan",
        "credits_requested",
        "payment_method",
        "tnxid",
        "amount_bdt",
        "status",
        "created_at",
    )
    list_filter = ("status", "kind", "payment_method")
    search_fields = ("tnxid", "user__username", "sender_number")
    actions = ["approve_selected_mfs_payments", "reject_selected_mfs_payments"]

    @admin.action(description="Approve selected MFS payments & credit users")
    def approve_selected_mfs_payments(self, request, queryset) -> None:
        approved = 0
        for req_obj in queryset.filter(status=MfsPaymentRequest.Status.PENDING):
            try:
                approve_mfs_payment_request(req_obj.pk, admin_user=request.user)
                approved += 1
            except (PaymentValidationError, PlanAlreadyActiveError):
                continue
        self.message_user(request, f"Approved {approved} MFS payment request(s).")

    @admin.action(description="Reject selected MFS payments")
    def reject_selected_mfs_payments(self, request, queryset) -> None:
        rejected = 0
        for req_obj in queryset.filter(status=MfsPaymentRequest.Status.PENDING):
            try:
                reject_mfs_payment_request(req_obj.pk, admin_user=request.user)
                rejected += 1
            except PaymentValidationError:
                continue
        self.message_user(request, f"Rejected {rejected} MFS payment request(s).")
