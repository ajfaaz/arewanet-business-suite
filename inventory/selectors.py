from core.selectors.base import BaseSelector
from inventory.models import (
    Warehouse, WarehouseLocation, InventoryItem, StockMovement,
    GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
)


class WarehouseSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return Warehouse.objects.filter(
            organization=organization
        ).prefetch_related("locations")

    @staticmethod
    def get_by_id(organization, warehouse_id):
        return Warehouse.objects.filter(
            organization=organization,
            id=warehouse_id,
        ).first()


class WarehouseLocationSelector(BaseSelector):
    @staticmethod
    def list(warehouse):
        return WarehouseLocation.objects.filter(
            warehouse=warehouse
        ).select_related("warehouse")


class InventorySelector(BaseSelector):
    @staticmethod
    def list(organization):
        return InventoryItem.objects.filter(
            organization=organization
        ).select_related("product", "warehouse", "location", "product__category")

    @staticmethod
    def get_for_product(organization, product):
        return InventoryItem.objects.filter(
            organization=organization,
            product=product,
        ).select_related("warehouse", "location")


class StockMovementSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return StockMovement.objects.filter(
            organization=organization
        ).select_related("product", "warehouse", "location")


class GoodsReceivedNoteSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return GoodsReceivedNote.objects.filter(
            organization=organization
        ).select_related("warehouse", "created_by", "approved_by", "completed_by").prefetch_related("items__product")


class GoodsIssueNoteSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return GoodsIssueNote.objects.filter(
            organization=organization
        ).select_related("warehouse", "created_by", "approved_by", "completed_by").prefetch_related("items__product")


class StockTransferDocumentSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return StockTransferDocument.objects.filter(
            organization=organization
        ).select_related("source_warehouse", "destination_warehouse", "created_by", "approved_by", "completed_by").prefetch_related("items__product")


class StockAdjustmentDocumentSelector(BaseSelector):
    @staticmethod
    def list(organization):
        return StockAdjustmentDocument.objects.filter(
            organization=organization
        ).select_related("warehouse", "created_by", "approved_by", "completed_by").prefetch_related("items__product")
