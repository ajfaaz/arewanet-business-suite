from rest_framework import serializers
from django.db.models import Sum
from invoices.models import Customer, Invoice, Quotation


class CustomerInvoiceSummarySerializer(serializers.ModelSerializer):
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_no",
            "invoice_date",
            "due_date",
            "total_due",
            "total_paid",
            "balance_due",
            "status",
        ]


class CustomerQuotationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = [
            "id",
            "quotation_no",
            "quotation_date",
            "valid_until",
            "total",
            "status",
        ]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class CustomerListSerializer(serializers.ModelSerializer):
    outstanding = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = (
            "id",
            "company_name",
            "contact_person",
            "phone",
            "email",
            "outstanding",
        )

    def get_outstanding(self, obj):
        invoices = obj.invoice_set.all()
        return sum((inv.balance_due for inv in invoices if inv.status != 'CANCELLED'), 0)


class CustomerDetailSerializer(serializers.ModelSerializer):
    invoices = CustomerInvoiceSummarySerializer(source="invoice_set", many=True, read_only=True)
    quotations = CustomerQuotationSummarySerializer(source="quotation_set", many=True, read_only=True)
    outstanding = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "outstanding",
            "total_paid",
            "invoices",
            "quotations",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")

    def get_outstanding(self, obj):
        invoices = obj.invoice_set.all()
        return sum((inv.balance_due for inv in invoices if inv.status != 'CANCELLED'), 0)

    def get_total_paid(self, obj):
        invoices = obj.invoice_set.all()
        return sum((inv.total_paid for inv in invoices), 0)
