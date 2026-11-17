"""REST views for checking and consuming user quota."""

from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import QuotaUsageLog
from .serializers import (
    ConsumeQuotaSerializer,
    QuotaUsageLogSerializer,
    UserQuotaSerializer,
)
from .services import InsufficientQuotaError, consume_user_quota, get_or_create_quota


class MyQuotaView(APIView):
    """Retrieve the authenticated user's current credit and rate-limit quota."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        quota = get_or_create_quota(request.user)
        return Response(UserQuotaSerializer(quota).data)


class ConsumeQuotaView(APIView):
    """Atomically deduct credits for an inference request."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ConsumeQuotaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            quota = consume_user_quota(
                user=request.user,
                credits=data["credits"],
                model_tier=data["model_tier"],
                task_type=data["task_type"],
                endpoint=data["endpoint"],
                latency_ms=data["latency_ms"],
            )
        except InsufficientQuotaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(UserQuotaSerializer(quota).data, status=status.HTTP_200_OK)


class QuotaLogsView(generics.ListAPIView):
    """List recent AI quota usage entries for the authenticated user."""

    serializer_class = QuotaUsageLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuotaUsageLog.objects.filter(user=self.request.user)[:50]

