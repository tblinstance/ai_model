"""Serializers for billing plans, subscriptions, and invoices."""

from rest_framework import serializers

from .models import Invoice, MfsPaymentRequest, Plan, Subscription
from .services import BDT_PER_USD, usd_to_bdt


class PlanSerializer(serializers.ModelSerializer):
    """Read serializer for billing plans including BDT pricing."""

    monthly_price_bdt = serializers.SerializerMethodField()
    bdt_rate = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "slug",
            "monthly_price_usd",
            "monthly_price_bdt",
            "bdt_rate",
            "monthly_credits",
            "daily_request_limit",
            "allowed_tiers",
            "description",
        ]

    def get_monthly_price_bdt(self, obj: Plan) -> str:
        return str(usd_to_bdt(obj.monthly_price_usd))

    def get_bdt_rate(self, obj: Plan) -> str:
        return str(BDT_PER_USD)


class SubscriptionSerializer(serializers.ModelSerializer):
    """Read serializer for a user's active subscription."""

    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "plan", "status", "started_at", "renews_at", "auto_renew"]


class SubscribeRequestSerializer(serializers.Serializer):
    """Payload to subscribe or upgrade to a billing plan via MFS (bKash/Nagad/Rocket/Upay)."""

    plan_slug = serializers.SlugField()
    currency = serializers.ChoiceField(choices=["USD", "BDT"], required=False, default="BDT")
    amount_bdt = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    payment_method = serializers.CharField(max_length=24, required=False, allow_blank=True, default="")
    tnxid = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class CheckoutVerifySerializer(serializers.Serializer):
    """Input payload for pre-checkout verification or post-checkout receipt verification."""

    mode = serializers.ChoiceField(choices=["credits", "plan", "receipt"])
    credits = serializers.IntegerField(min_value=10, max_value=100000, required=False)
    amount_usd = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    amount_bdt = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    payment_method = serializers.CharField(max_length=24, required=False, allow_blank=True, default="")
    tnxid = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    plan_slug = serializers.SlugField(required=False)
    reference = serializers.CharField(max_length=64, required=False, allow_blank=False)

    def validate(self, attrs):
        mode = attrs.get("mode")
        if mode == "credits" and attrs.get("credits") is None:
            raise serializers.ValidationError({"credits": "This field is required when mode is 'credits'."})
        if mode == "plan" and not attrs.get("plan_slug"):
            raise serializers.ValidationError({"plan_slug": "This field is required when mode is 'plan'."})
        if mode == "receipt" and not attrs.get("reference"):
            raise serializers.ValidationError({"reference": "This field is required when mode is 'receipt'."})
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    """Read serializer for user invoices."""

    username = serializers.CharField(source="user.username", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "username",
            "invoice_number",
            "plan_name",
            "currency",
            "amount_usd",
            "amount_bdt",
            "payment_method",
            "tnxid",
            "credits_granted",
            "status",
            "created_at",
        ]


class MfsPaymentRequestSerializer(serializers.ModelSerializer):
    """Read serializer for member-submitted BDT MFS payment requests."""

    username = serializers.CharField(source="user.username", read_only=True)
    plan_slug = serializers.CharField(source="plan.slug", read_only=True, default="")
    plan_name = serializers.CharField(source="plan.name", read_only=True, default="")
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, default="")
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True, default="")

    class Meta:
        model = MfsPaymentRequest
        fields = [
            "id",
            "username",
            "kind",
            "plan_slug",
            "plan_name",
            "credits_requested",
            "currency",
            "amount_usd",
            "amount_bdt",
            "payment_method",
            "tnxid",
            "sender_number",
            "status",
            "admin_note",
            "reviewed_by_username",
            "reviewed_at",
            "invoice_number",
            "created_at",
        ]


class MfsPaymentCreateSerializer(serializers.Serializer):
    """Payload for submitting a bKash/Nagad/Rocket/Upay BDT payment for verification."""

    kind = serializers.ChoiceField(choices=["credits", "plan"])
    credits = serializers.IntegerField(min_value=10, max_value=100000, required=False, default=0)
    plan_slug = serializers.SlugField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(choices=["bkash", "nagad", "rocket", "upay"])
    tnxid = serializers.CharField(max_length=64, allow_blank=False)
    amount_bdt = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    sender_number = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["kind"] == "credits" and attrs.get("credits", 0) < 10:
            raise serializers.ValidationError({"credits": "Enter between 10 and 100,000 credits."})
        if attrs["kind"] == "plan" and not attrs.get("plan_slug"):
            raise serializers.ValidationError({"plan_slug": "This field is required when kind is 'plan'."})
        return attrs


class AdminReviewMfsSerializer(serializers.Serializer):
    """Optional note when approving or rejecting a pending MFS payment request."""

    admin_note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class AdminGrantCreditsSerializer(serializers.Serializer):
    """Payload for admin-granted member credits."""

    user_id = serializers.IntegerField(min_value=1)
    credits = serializers.IntegerField(min_value=1, max_value=1000000)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class AdminClearBalanceSerializer(serializers.Serializer):
    """Payload for clearing a user's credit balance to 0."""

    user_id = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class AdminSwitchPlanSerializer(serializers.Serializer):
    """Payload for admin-initiated member plan assignment."""

    user_id = serializers.IntegerField(min_value=1)
    plan_slug = serializers.SlugField()


