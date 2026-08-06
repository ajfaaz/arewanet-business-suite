from rest_framework import serializers
from sales.payments.models import Payment, PaymentAllocation
from api.serializers.customer import CustomerSerializer


class PaymentAllocationSerializer(serializers.ModelSerializer):
    invoice_no = serializers.ReadOnlyField(source="invoice.invoice_no")

    class Meta:
        model = PaymentAllocation
        fields = [
            "id",
            "invoice",
            "invoice_no",
            "amount",
            "created_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Payment
        fields = [
            "id",
            "receipt_number",
            "customer",
            "customer_detail",
            "invoice",
            "invoice_id",
            "amount",
            "payment_date",
            "payment_method",
            "reference",
            "status",
            "notes",
            "allocations",
            "created_at",
        ]
        read_only_fields = ["id", "receipt_number", "invoice", "status", "created_at"]
