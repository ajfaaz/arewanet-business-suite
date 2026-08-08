from django.contrib import admin
from inventory.models import Warehouse, WarehouseLocation, InventoryItem, StockMovement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code", "organization__name")


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "warehouse", "is_active", "created_at")
    list_filter = ("warehouse__organization", "warehouse", "is_active")
    search_fields = ("name", "code", "warehouse__name")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "location", "quantity", "organization", "updated_at")
    list_filter = ("organization", "warehouse")
    search_fields = ("product__name", "product__sku", "warehouse__name", "location__name")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "movement_type", "product", "quantity", "warehouse", "organization")
    list_filter = ("organization", "movement_type", "warehouse")
    search_fields = ("product__name", "product__sku", "warehouse__name", "reference_type")
    readonly_fields = ("created_at",)
