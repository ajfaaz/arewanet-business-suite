from rest_framework import serializers
from invoices.models import Invoice, InvoiceItem
from api.serializers.customer import CustomerSerializer


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "description",
            "unit",
            "qty",
            "unit_price",
            "total",
        ]
        read_only_fields = ["id", "total"]


class InvoiceSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    items = InvoiceItemSerializer(many=True, required=False)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_no",
            "customer",
            "customer_detail",
            "invoice_date",
            "due_date",
            "project_name",
            "deployment_phase",
            "status",
            "subtotal",
            "vat",
            "total_due",
            "total_paid",
            "balance_due",
            "items",
            "created_at",
        ]
        read_only_fields = ["id", "invoice_no", "subtotal", "total_due", "total_paid", "balance_due", "created_at"]


class InvoicePaySerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField(max_length=20, default="BANK")
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
