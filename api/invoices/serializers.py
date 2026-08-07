from rest_framework import serializers
from invoices.models import Invoice, InvoiceItem, Customer, Product


class CustomerNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "company_name", "contact_person", "email", "phone", "address"]


class ProductNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "selling_price", "unit"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_detail = ProductNestedSerializer(source="product", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "product",
            "product_detail",
            "description",
            "qty",
            "unit_price",
            "total",
        ]
        read_only_fields = ("total",)


class InvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.company_name",
        read_only=True
    )
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_no",
            "customer",
            "customer_name",
            "invoice_date",
            "due_date",
            "status",
            "total_due",
            "total_paid",
            "balance_due",
        )


class InvoiceDetailSerializer(serializers.ModelSerializer):
    customer = CustomerNestedSerializer(read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        exclude = ("organization",)
        extra_kwargs = {
            "invoice_no": {"required": False, "allow_blank": True}
        }
