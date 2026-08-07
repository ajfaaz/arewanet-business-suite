from rest_framework import serializers
from invoices.models import Quotation, QuotationItem, Customer, Product


class CustomerNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "company_name", "contact_person", "email", "phone", "address"]


class ProductNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "selling_price", "unit"]


class QuotationItemSerializer(serializers.ModelSerializer):
    product_detail = ProductNestedSerializer(source="product", read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            "id",
            "product",
            "product_detail",
            "description",
            "qty",
            "unit_price",
            "discount",
            "total",
        ]
        read_only_fields = ("total",)


class QuotationListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.company_name",
        read_only=True
    )

    class Meta:
        model = Quotation
        fields = (
            "id",
            "quotation_no",
            "customer",
            "customer_name",
            "quotation_date",
            "valid_until",
            "status",
            "subtotal",
            "total",
        )


class QuotationDetailSerializer(serializers.ModelSerializer):
    customer = CustomerNestedSerializer(read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Quotation
        fields = "__all__"


class QuotationCreateSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, required=False)

    class Meta:
        model = Quotation
        exclude = ("organization",)
        extra_kwargs = {
            "quotation_no": {"required": False, "allow_blank": True}
        }
