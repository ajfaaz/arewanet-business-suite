from rest_framework import serializers

from inventory.models import StockMovement


class StockLedgerMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )
    warehouse_code = serializers.CharField(
        source="warehouse.code",
        read_only=True,
    )
    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        default=None,
    )
    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
        default=None,
    )

    quantity_in = serializers.SerializerMethodField()
    quantity_out = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "created_at",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "location",
            "location_name",
            "location_code",
            "movement_type",
            "quantity",
            "quantity_in",
            "quantity_out",
            "reference_type",
            "reference_id",
            "notes",
        ]

    def get_quantity_in(self, obj):
        return obj.quantity if obj.quantity > 0 else 0

    def get_quantity_out(self, obj):
        return abs(obj.quantity) if obj.quantity < 0 else 0
