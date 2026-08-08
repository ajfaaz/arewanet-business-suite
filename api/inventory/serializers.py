from rest_framework import serializers
from inventory.models import (
    Warehouse, WarehouseLocation, InventoryItem, StockMovement,
    GoodsReceivedNote, GoodsReceivedNoteItem,
    GoodsIssueNote, GoodsIssueNoteItem,
    StockTransferDocument, StockTransferDocumentItem,
    StockAdjustmentDocument, StockAdjustmentDocumentItem,
)
from invoices.models import Product


class WarehouseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseLocation
        fields = ["id", "warehouse", "name", "code", "is_active", "created_at", "updated_at"]
        read_only_fields = ("id", "created_at", "updated_at")


class WarehouseSerializer(serializers.ModelSerializer):
    locations = WarehouseLocationSerializer(many=True, read_only=True)

    class Meta:
        model = Warehouse
        fields = ["id", "organization", "name", "code", "address", "is_active", "locations", "created_at", "updated_at"]
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default=None)
    location_code = serializers.CharField(source="location.code", read_only=True, default=None)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "location",
            "location_name",
            "location_code",
            "quantity",
            "updated_at",
        ]
        read_only_fields = ("id", "quantity", "updated_at")


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default=None)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "organization",
            "product",
            "product_name",
            "warehouse",
            "warehouse_name",
            "location",
            "location_name",
            "quantity",
            "movement_type",
            "movement_type_display",
            "reference_type",
            "reference_id",
            "notes",
            "created_at",
        ]
        read_only_fields = ("id", "organization", "created_at")


class StockOperationSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    warehouse = serializers.IntegerField()
    location = serializers.IntegerField(required=False, allow_null=True, default=None)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    reference_type = serializers.CharField(required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class StockAdjustmentSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    warehouse = serializers.IntegerField()
    location = serializers.IntegerField(required=False, allow_null=True, default=None)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    reference_type = serializers.CharField(required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Adjustment new quantity cannot be negative.")
        return value


class StockTransferSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    from_warehouse = serializers.IntegerField()
    to_warehouse = serializers.IntegerField()
    from_location = serializers.IntegerField(required=False, allow_null=True, default=None)
    to_location = serializers.IntegerField(required=False, allow_null=True, default=None)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    reference_type = serializers.CharField(required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate(self, attrs):
        if attrs["from_warehouse"] == attrs["to_warehouse"] and attrs.get("from_location") == attrs.get("to_location"):
            raise serializers.ValidationError("Source and Destination warehouse/location must be different.")
        return attrs


# -------------------------------------------------------------------------
# Inventory Document Serializers
# -------------------------------------------------------------------------

class GoodsReceivedNoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = GoodsReceivedNoteItem
        fields = ["id", "product", "product_name", "product_sku", "quantity", "unit_cost"]


class GoodsReceivedNoteSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True, default=None)
    completed_by_username = serializers.CharField(source="completed_by.username", read_only=True, default=None)
    items = GoodsReceivedNoteItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceivedNote
        fields = [
            "id",
            "organization",
            "document_number",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "supplier_name",
            "received_date",
            "status",
            "notes",
            "created_by",
            "created_by_username",
            "approved_by",
            "approved_by_username",
            "completed_by",
            "completed_by_username",
            "items",
            "created_at",
            "updated_at",
            "approved_at",
            "completed_at",
        ]
        read_only_fields = ("id", "organization", "document_number", "status", "created_at", "updated_at", "approved_at", "completed_at")


class GoodsIssueNoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = GoodsIssueNoteItem
        fields = ["id", "product", "product_name", "product_sku", "quantity"]


class GoodsIssueNoteSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True, default=None)
    completed_by_username = serializers.CharField(source="completed_by.username", read_only=True, default=None)
    items = GoodsIssueNoteItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsIssueNote
        fields = [
            "id",
            "organization",
            "document_number",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "issue_date",
            "status",
            "notes",
            "created_by",
            "created_by_username",
            "approved_by",
            "approved_by_username",
            "completed_by",
            "completed_by_username",
            "items",
            "created_at",
            "updated_at",
            "approved_at",
            "completed_at",
        ]
        read_only_fields = ("id", "organization", "document_number", "status", "created_at", "updated_at", "approved_at", "completed_at")


class StockTransferDocumentItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = StockTransferDocumentItem
        fields = ["id", "product", "product_name", "product_sku", "quantity"]


class StockTransferDocumentSerializer(serializers.ModelSerializer):
    source_warehouse_name = serializers.CharField(source="source_warehouse.name", read_only=True)
    destination_warehouse_name = serializers.CharField(source="destination_warehouse.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True, default=None)
    completed_by_username = serializers.CharField(source="completed_by.username", read_only=True, default=None)
    items = StockTransferDocumentItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockTransferDocument
        fields = [
            "id",
            "organization",
            "document_number",
            "source_warehouse",
            "source_warehouse_name",
            "destination_warehouse",
            "destination_warehouse_name",
            "transfer_date",
            "status",
            "notes",
            "created_by",
            "created_by_username",
            "approved_by",
            "approved_by_username",
            "completed_by",
            "completed_by_username",
            "items",
            "created_at",
            "updated_at",
            "approved_at",
            "completed_at",
        ]
        read_only_fields = ("id", "organization", "document_number", "status", "created_at", "updated_at", "approved_at", "completed_at")


class StockAdjustmentDocumentItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = StockAdjustmentDocumentItem
        fields = ["id", "product", "product_name", "product_sku", "system_quantity", "counted_quantity", "difference", "reason"]


class StockAdjustmentDocumentSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True, default=None)
    completed_by_username = serializers.CharField(source="completed_by.username", read_only=True, default=None)
    items = StockAdjustmentDocumentItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockAdjustmentDocument
        fields = [
            "id",
            "organization",
            "document_number",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "adjustment_date",
            "status",
            "notes",
            "created_by",
            "created_by_username",
            "approved_by",
            "approved_by_username",
            "completed_by",
            "completed_by_username",
            "items",
            "created_at",
            "updated_at",
            "approved_at",
            "completed_at",
        ]
        read_only_fields = ("id", "organization", "document_number", "status", "created_at", "updated_at", "approved_at", "completed_at")
