from rest_framework import serializers
from invoices.models import Quotation, QuotationItem
from api.serializers.customer import CustomerSerializer


class QuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItem
        fields = [
            "id",
            "description",
            "qty",
            "unit_price",
            "total",
        ]
        read_only_fields = ["id", "total"]


class QuotationSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    items = QuotationItemSerializer(many=True, required=False)

    class Meta:
        model = Quotation
        fields = [
            "id",
            "quotation_no",
            "customer",
            "customer_detail",
            "quotation_date",
            "valid_until",
            "status",
            "subtotal",
            "vat",
            "discount",
            "total",
            "notes",
            "terms",
            "items",
            "created_at",
        ]
        read_only_fields = ["id", "quotation_no", "subtotal", "total", "created_at"]
