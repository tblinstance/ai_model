"""Serializers for the transactions app."""

from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """Read serializer for transaction ledger entries."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "username",
            "reference_id",
            "tx_type",
            "currency",
            "amount_usd",
            "amount_bdt",
            "payment_method",
            "tnxid",
            "credits_delta",
            "balance_after",
            "model_tier",
            "task_type",
            "description",
            "metadata",
            "created_at",
        ]


class TopUpSerializer(serializers.Serializer):
    """Input payload for purchasing or topping up credit packs."""

    credits = serializers.IntegerField(min_value=10, max_value=100000)
    currency = serializers.ChoiceField(choices=["USD", "BDT"], required=False, default="BDT")
    amount_usd = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    amount_bdt = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    payment_method = serializers.CharField(max_length=24, required=False, allow_blank=True, default="")
    tnxid = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")

