from rest_framework import serializers
from purchases.models import PurchaseOrder, PurchaseOrderItem, Supplier
from inventory.models import Warehouse
from invoices.models import Product


class SupplierNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "code", "company_name", "contact_person", "email", "phone"]


class WarehouseNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name"]


class ProductNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "selling_price", "unit"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductNestedSerializer(source="product", read_only=True)
    remaining_quantity = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "product",
            "product_detail",
            "quantity",
            "unit_cost",
            "total_cost",
            "received_quantity",
            "remaining_quantity",
        ]
        read_only_fields = ["total_cost", "received_quantity"]


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "order_number",
            "supplier",
            "supplier_name",
            "warehouse",
            "warehouse_name",
            "order_date",
            "expected_date",
            "status",
            "total",
            "created_at",
        ]


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    supplier = SupplierNestedSerializer(read_only=True)
    warehouse = WarehouseNestedSerializer(read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "order_number",
            "supplier",
            "warehouse",
            "order_date",
            "expected_date",
            "status",
            "notes",
            "subtotal",
            "tax",
            "total",
            "items",
            "created_at",
            "updated_at",
        ]


class PurchaseOrderCreateItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=15, decimal_places=2)


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    items = PurchaseOrderCreateItemSerializer(many=True, write_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier",
            "warehouse",
            "order_date",
            "expected_date",
            "notes",
            "items",
        ]
