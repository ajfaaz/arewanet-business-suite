from rest_framework import serializers
from sales.subscriptions.models import Subscription, SubscriptionItem, SubscriptionTemplate
from api.serializers.customer import CustomerSerializer


class SubscriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionItem
        fields = [
            "id",
            "product",
            "description",
            "qty",
            "unit_price",
            "discount",
            "total",
        ]
        read_only_fields = ["id", "total"]


class SubscriptionSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    items = SubscriptionItemSerializer(many=True, required=False)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    mrr = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    arr = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "title",
            "customer",
            "customer_detail",
            "template",
            "start_date",
            "end_date",
            "billing_cycle",
            "next_invoice_date",
            "auto_generate",
            "status",
            "is_active",
            "total_amount",
            "mrr",
            "arr",
            "notes",
            "items",
            "created_at",
        ]
        read_only_fields = ["id", "next_invoice_date", "total_amount", "mrr", "arr", "created_at"]


class SubscriptionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTemplate
        fields = [
            "id",
            "title",
            "billing_cycle",
            "description",
            "is_active",
        ]
