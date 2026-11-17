"""URL routes for billing app."""

from django.urls import path

from .views import (
    AdminBillingOverviewView,
    AdminClearBalanceView,
    AdminGrantCreditsView,
    AdminMfsRequestApproveView,
    AdminMfsRequestRejectView,
    AdminSwitchPlanView,
    CheckoutVerifyView,
    CurrentSubscriptionView,
    InvoiceListView,
    MemberMfsRequestListCreateView,
    PlanListView,
    SubscribePlanView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="billing-plans"),
    path("subscription/", CurrentSubscriptionView.as_view(), name="billing-subscription"),
    path("subscribe/", SubscribePlanView.as_view(), name="billing-subscribe"),
    path("checkout/verify/", CheckoutVerifyView.as_view(), name="billing-checkout-verify"),
    path("invoices/", InvoiceListView.as_view(), name="billing-invoices"),
    path("mfs-requests/", MemberMfsRequestListCreateView.as_view(), name="billing-mfs-requests"),
    path("admin/overview/", AdminBillingOverviewView.as_view(), name="billing-admin-overview"),
    path("admin/mfs-requests/<int:pk>/approve/", AdminMfsRequestApproveView.as_view(), name="billing-admin-mfs-approve"),
    path("admin/mfs-requests/<int:pk>/reject/", AdminMfsRequestRejectView.as_view(), name="billing-admin-mfs-reject"),
    path("admin/grant-credits/", AdminGrantCreditsView.as_view(), name="billing-admin-grant-credits"),
    path("admin/clear-balance/", AdminClearBalanceView.as_view(), name="billing-admin-clear-balance"),
    path("admin/switch-plan/", AdminSwitchPlanView.as_view(), name="billing-admin-switch-plan"),
]

