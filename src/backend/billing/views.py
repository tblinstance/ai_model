"""REST views for plans, subscriptions, and invoices."""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from quota.models import UserQuota
from quota.serializers import UserQuotaSerializer
from quota.services import get_or_create_quota
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer
from .models import Invoice, MfsPaymentRequest, Plan, Subscription
from .serializers import (
    AdminClearBalanceSerializer,
    AdminGrantCreditsSerializer,
    AdminReviewMfsSerializer,
    AdminSwitchPlanSerializer,
    CheckoutVerifySerializer,
    InvoiceSerializer,
    MfsPaymentCreateSerializer,
    MfsPaymentRequestSerializer,
    PlanSerializer,
    SubscribeRequestSerializer,
    SubscriptionSerializer,
)
from .services import (
    PaymentValidationError,
    PlanAlreadyActiveError,
    admin_clear_member_balance,
    admin_grant_member_credits,
    approve_mfs_payment_request,
    create_mfs_payment_request,
    ensure_default_plans,
    get_or_create_subscription,
    reject_mfs_payment_request,
    subscribe_user_to_plan,
    verify_checkout_request,
)


class PlanListView(generics.ListAPIView):
    """List all active subscription plans (auto-seeds defaults if empty)."""

    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not Plan.objects.exists():
            ensure_default_plans()
        return Plan.objects.filter(is_active=True)


class CurrentSubscriptionView(APIView):
    """Return the authenticated user's active subscription."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        subscription = get_or_create_subscription(request.user)
        if subscription is None:
            return Response({"subscription": None})
        return Response(SubscriptionSerializer(subscription).data)


class SubscribePlanView(APIView):
    """Switch or upgrade the authenticated user's billing plan."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not Plan.objects.exists():
            ensure_default_plans()
        serializer = SubscribeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(Plan, slug=serializer.validated_data["plan_slug"], is_active=True)
        try:
            subscription, invoice = subscribe_user_to_plan(
                request.user,
                plan,
                payment_method=serializer.validated_data.get("payment_method", ""),
                tnxid=serializer.validated_data.get("tnxid", ""),
                currency=serializer.validated_data.get("currency"),
                amount_bdt=serializer.validated_data.get("amount_bdt"),
            )
        except (PlanAlreadyActiveError, PaymentValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        quota_obj = get_or_create_quota(request.user)
        return Response(
            {
                "checkout_verified": True,
                "subscription": SubscriptionSerializer(subscription).data,
                "invoice": InvoiceSerializer(invoice).data,
                "quota": UserQuotaSerializer(quota_obj).data,
            },
            status=status.HTTP_200_OK,
        )


class CheckoutVerifyView(APIView):
    """Verify balance eligibility, pricing parity, or checkout receipt signatures."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not Plan.objects.exists():
            ensure_default_plans()
        serializer = CheckoutVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            report = verify_checkout_request(
                request.user,
                mode=data["mode"],
                credits=data.get("credits"),
                amount_usd=data.get("amount_usd"),
                amount_bdt=data.get("amount_bdt"),
                payment_method=data.get("payment_method"),
                tnxid=data.get("tnxid"),
                plan_slug=data.get("plan_slug"),
                reference=data.get("reference"),
            )
        except (Plan.DoesNotExist, Invoice.DoesNotExist) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(report, status=status.HTTP_200_OK)


class InvoiceListView(generics.ListAPIView):
    """List historical invoices for the authenticated user."""

    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).select_related("user", "plan")[:50]


class MemberMfsRequestListCreateView(APIView):
    """List own MFS payment requests or submit a new bKash/Nagad/Rocket/Upay BDT payment for approval."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = MfsPaymentRequest.objects.filter(user=request.user).select_related(
            "user", "plan", "reviewed_by", "invoice"
        )[:50]
        return Response(MfsPaymentRequestSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        if not Plan.objects.exists():
            ensure_default_plans()
        serializer = MfsPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = None
        if data["kind"] == "plan":
            plan = get_object_or_404(Plan, slug=data["plan_slug"], is_active=True)

        try:
            req_obj = create_mfs_payment_request(
                request.user,
                kind=data["kind"],
                payment_method=data["payment_method"],
                tnxid=data["tnxid"],
                credits=data.get("credits", 0),
                plan=plan,
                amount_bdt=data.get("amount_bdt"),
                sender_number=data.get("sender_number", ""),
            )
        except (PlanAlreadyActiveError, PaymentValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "checkout_status": req_obj.status,
                "request": MfsPaymentRequestSerializer(req_obj).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminBillingOverviewView(APIView):
    """Admin-only view returning all users, pending/completed MFS requests, invoices, and transactions."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request: Request) -> Response:
        User = get_user_model()
        users_qs = User.objects.order_by("id").all()
        quotas = {q.user_id: q for q in UserQuota.objects.all()}
        subs = {s.user_id: s for s in Subscription.objects.select_related("plan").all()}

        users_payload = []
        for u in users_qs:
            q = quotas.get(u.id)
            s = subs.get(u.id)
            users_payload.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "is_staff": u.is_staff,
                    "is_superuser": u.is_superuser,
                    "is_active": u.is_active,
                    "date_joined": u.date_joined,
                    "plan_slug": s.plan.slug if s else "free",
                    "plan_name": s.plan.name if s else "Free",
                    "remaining_credits": q.remaining_credits if q else 0,
                    "total_credits": q.total_credits if q else 0,
                    "daily_requests": q.daily_requests if q else 0,
                    "max_daily_requests": q.max_daily_requests if q else 250,
                }
            )

        status_filter = str(request.query_params.get("status", "")).strip().lower()
        mfs_qs = MfsPaymentRequest.objects.select_related(
            "user", "plan", "reviewed_by", "invoice"
        ).all()
        if status_filter in ("pending", "approved", "rejected"):
            mfs_qs = mfs_qs.filter(status=status_filter)

        invoices_qs = Invoice.objects.select_related("user", "plan").all()[:100]
        tx_qs = Transaction.objects.select_related("user").all()[:120]

        pending_cnt = MfsPaymentRequest.objects.filter(status=MfsPaymentRequest.Status.PENDING).count()
        approved_cnt = MfsPaymentRequest.objects.filter(status=MfsPaymentRequest.Status.APPROVED).count()
        rejected_cnt = MfsPaymentRequest.objects.filter(status=MfsPaymentRequest.Status.REJECTED).count()

        tx_agg = Transaction.objects.aggregate(
            usd=Sum("amount_usd"),
            bdt=Sum("amount_bdt"),
        )
        total_credits = sum(u["remaining_credits"] for u in users_payload)

        return Response(
            {
                "summary": {
                    "total_users": len(users_payload),
                    "pending_requests": pending_cnt,
                    "approved_requests": approved_cnt,
                    "rejected_requests": rejected_cnt,
                    "total_revenue_usd": float(tx_agg["usd"] or Decimal("0.00")),
                    "total_revenue_bdt": float(tx_agg["bdt"] or Decimal("0.00")),
                    "total_credits_balance": total_credits,
                },
                "users": users_payload,
                "mfs_requests": MfsPaymentRequestSerializer(mfs_qs[:100], many=True).data,
                "invoices": InvoiceSerializer(invoices_qs, many=True).data,
                "transactions": TransactionSerializer(tx_qs, many=True).data,
            }
        )


class AdminMfsRequestApproveView(APIView):
    """Admin approves a member BDT MFS payment, applying quota & subscription changes atomically."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request: Request, pk: int) -> Response:
        serializer = AdminReviewMfsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = approve_mfs_payment_request(
                pk,
                admin_user=request.user,
                admin_note=serializer.validated_data.get("admin_note", ""),
            )
        except MfsPaymentRequest.DoesNotExist:
            return Response({"detail": "MFS payment request not found."}, status=status.HTTP_404_NOT_FOUND)
        except (PaymentValidationError, PlanAlreadyActiveError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        quota_obj = get_or_create_quota(updated.user)
        return Response(
            {
                "request": MfsPaymentRequestSerializer(updated).data,
                "member_quota": UserQuotaSerializer(quota_obj).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminMfsRequestRejectView(APIView):
    """Admin rejects a pending member BDT MFS payment without modifying credits."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request: Request, pk: int) -> Response:
        serializer = AdminReviewMfsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = reject_mfs_payment_request(
                pk,
                admin_user=request.user,
                admin_note=serializer.validated_data.get("admin_note", ""),
            )
        except MfsPaymentRequest.DoesNotExist:
            return Response({"detail": "MFS payment request not found."}, status=status.HTTP_404_NOT_FOUND)
        except PaymentValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"request": MfsPaymentRequestSerializer(updated).data}, status=status.HTTP_200_OK)


class AdminGrantCreditsView(APIView):
    """Admin grants bonus/adjustment credits directly to any user account."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request: Request) -> Response:
        serializer = AdminGrantCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User = get_user_model()
        target_user = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        quota_obj, tx = admin_grant_member_credits(
            target_user,
            credits=serializer.validated_data["credits"],
            admin_user=request.user,
            description=serializer.validated_data.get("description", ""),
        )
        return Response(
            {
                "quota": UserQuotaSerializer(quota_obj).data,
                "transaction": TransactionSerializer(tx).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminClearBalanceView(APIView):
    """Admin clears a user's credit balance to 0 cleanly with an offsetting ledger entry."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request: Request) -> Response:
        serializer = AdminClearBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User = get_user_model()
        target_user = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        quota_obj, tx, cleared_credits = admin_clear_member_balance(
            target_user,
            admin_user=request.user,
            description=serializer.validated_data.get("description", ""),
        )
        return Response(
            {
                "quota": UserQuotaSerializer(quota_obj).data,
                "cleared_credits": cleared_credits,
                "transaction": TransactionSerializer(tx).data if tx else None,
            },
            status=status.HTTP_200_OK,
        )


class AdminSwitchPlanView(APIView):
    """Admin switches any user's subscription plan directly."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request: Request) -> Response:
        if not Plan.objects.exists():
            ensure_default_plans()
        serializer = AdminSwitchPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User = get_user_model()
        target_user = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        plan = get_object_or_404(Plan, slug=serializer.validated_data["plan_slug"], is_active=True)
        try:
            sub, invoice = subscribe_user_to_plan(target_user, plan)
        except PlanAlreadyActiveError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        quota_obj = get_or_create_quota(target_user)
        return Response(
            {
                "subscription": SubscriptionSerializer(sub).data,
                "invoice": InvoiceSerializer(invoice).data,
                "quota": UserQuotaSerializer(quota_obj).data,
            },
            status=status.HTTP_200_OK,
        )

