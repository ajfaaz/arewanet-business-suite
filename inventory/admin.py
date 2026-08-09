from django.contrib import admin
from inventory.models import (
    Warehouse, WarehouseLocation, InventoryItem, StockMovement,
    GoodsReceivedNote, GoodsReceivedNoteItem,
    GoodsIssueNote, GoodsIssueNoteItem,
    StockTransferDocument, StockTransferDocumentItem,
    StockTransferDocument, StockTransferDocumentItem,
    StockAdjustmentDocument, StockAdjustmentDocumentItem, StockAlert,
)


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("alert_type", "product", "warehouse", "current_quantity", "threshold", "is_resolved", "organization", "created_at")
    list_filter = ("organization", "alert_type", "is_resolved", "warehouse")
    search_fields = ("product__name", "product__sku", "warehouse__name")


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


class GRNItemInline(admin.TabularInline):
    model = GoodsReceivedNoteItem
    extra = 1


@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = ("document_number", "organization", "warehouse", "supplier_name", "status", "received_date", "created_at")
    list_filter = ("organization", "status", "warehouse")
    search_fields = ("document_number", "supplier_name", "warehouse__name")
    inlines = [GRNItemInline]


class GINItemInline(admin.TabularInline):
    model = GoodsIssueNoteItem
    extra = 1


@admin.register(GoodsIssueNote)
class GoodsIssueNoteAdmin(admin.ModelAdmin):
    list_display = ("document_number", "organization", "warehouse", "status", "issue_date", "created_at")
    list_filter = ("organization", "status", "warehouse")
    search_fields = ("document_number", "warehouse__name")
    inlines = [GINItemInline]


class TransferItemInline(admin.TabularInline):
    model = StockTransferDocumentItem
    extra = 1


@admin.register(StockTransferDocument)
class StockTransferDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_number", "organization", "source_warehouse", "destination_warehouse", "status", "transfer_date", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("document_number", "source_warehouse__name", "destination_warehouse__name")
    inlines = [TransferItemInline]


class AdjustmentItemInline(admin.TabularInline):
    model = StockAdjustmentDocumentItem
    extra = 1


@admin.register(StockAdjustmentDocument)
class StockAdjustmentDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_number", "organization", "warehouse", "status", "adjustment_date", "created_at")
    list_filter = ("organization", "status", "warehouse")
    search_fields = ("document_number", "warehouse__name")
    inlines = [AdjustmentItemInline]
