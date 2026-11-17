"""REST views for inspecting transactions and purchasing credit packs."""

from decimal import Decimal
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.services import (
    MFS_PAYMENT_METHODS,
    PaymentValidationError,
    compute_credit_pack_usd,
    sign_billing_event,
    validate_mfs_payment,
)
from quota.serializers import UserQuotaSerializer
from quota.services import grant_credits
from .models import Transaction
from .serializers import TopUpSerializer, TransactionSerializer
from .services import summarize_user_transactions


class TransactionListView(generics.ListAPIView):
    """List the authenticated user's credit and billing transactions."""

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)
        tx_type = self.request.query_params.get("tx_type")
        if tx_type:
            qs = qs.filter(tx_type=tx_type)
        return qs[:100]


class TransactionSummaryView(APIView):
    """Return aggregate spend and credit usage statistics."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(summarize_user_transactions(request.user))


class TopUpCreditsView(APIView):
    """Add credits to the user's quota balance and record a purchase transaction."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = TopUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credits = serializer.validated_data["credits"]
        expected_usd = compute_credit_pack_usd(credits)
        client_usd = serializer.validated_data.get("amount_usd")
        if client_usd is not None and Decimal(client_usd).quantize(Decimal("0.01")) != expected_usd:
            return Response(
                {
                    "detail": f"Checkout amount mismatch: expected ${expected_usd} for {credits} credits.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        amount_usd = expected_usd
        try:
            payment = validate_mfs_payment(
                serializer.validated_data.get("payment_method"),
                serializer.validated_data.get("tnxid"),
                expected_usd=amount_usd,
                currency=serializer.validated_data.get("currency"),
                amount_bdt=serializer.validated_data.get("amount_bdt"),
            )
        except PaymentValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        reference_tag = f"topup-{request.user.id}-{credits}"
        signature = sign_billing_event(
            user_id=request.user.id,
            reference=reference_tag,
            amount_usd=str(amount_usd),
            credits=credits,
        )
        method_label = MFS_PAYMENT_METHODS.get(payment["payment_method"], "")
        via_suffix = f" via {method_label} ({payment['tnxid']})" if method_label and payment["tnxid"] else ""
        quota_obj, tx = grant_credits(
            user=request.user,
            credits=credits,
            tx_type=Transaction.TxType.CREDIT_PURCHASE,
            amount_usd=amount_usd,
            amount_bdt=payment["amount_bdt"],
            currency=payment["currency"],
            payment_method=payment["payment_method"],
            tnxid=payment["tnxid"],
            description=f"Purchased {credits} AI credits{via_suffix}",
            metadata={
                "receipt_signature": signature,
                "payment_method": payment["payment_method"],
                "tnxid": payment["tnxid"],
                "amount_bdt": str(payment["amount_bdt"]),
                "currency": payment["currency"],
            },
        )
        return Response(
            {
                "checkout_verified": True,
                "remaining_credits": quota_obj.remaining_credits,
                "quota": UserQuotaSerializer(quota_obj).data,
                "transaction": TransactionSerializer(tx).data,
            },
            status=status.HTTP_201_CREATED,
        )

