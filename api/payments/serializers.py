from rest_framework import serializers
from sales.payments.models import Payment
from invoices.models import Customer, Invoice


class CustomerNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "company_name", "contact_person", "email", "phone"]


class InvoiceNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "invoice_no", "invoice_date", "total_due", "status"]


class PaymentListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.company_name",
        read_only=True
    )
    invoice_no = serializers.CharField(
        source="invoice.invoice_no",
        read_only=True
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "receipt_number",
            "customer",
            "customer_name",
            "invoice",
            "invoice_no",
            "amount",
            "payment_method",
            "payment_date",
            "status",
        )


class PaymentDetailSerializer(serializers.ModelSerializer):
    customer = CustomerNestedSerializer(read_only=True)
    invoice = InvoiceNestedSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"


class PaymentCreateSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        required=False,
        allow_null=True
    )
    payment_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Payment
        exclude = ("organization", "receipt_number", "status", "created_by")
