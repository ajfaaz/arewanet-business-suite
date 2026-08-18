from django.db.models import Q, Sum
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


class StockLedgerSelector:

    @classmethod
    def list(
        cls,
        organization,
        product=None,
        warehouse=None,
        location=None,
        movement_type=None,
        reference_type=None,
        start_date=None,
        end_date=None,
    ):
        """
        Return stock movements belonging to an organization.

        All filters are optional.
        """

        queryset = StockMovement.objects.filter(
            organization=organization
        ).select_related(
            "product",
            "warehouse",
            "location",
        )

        if product is not None:
            queryset = queryset.filter(product=product)

        if warehouse is not None:
            queryset = queryset.filter(warehouse=warehouse)

        if location is not None:
            queryset = queryset.filter(location=location)

        if movement_type:
            queryset = queryset.filter(
                movement_type=movement_type
            )

        if reference_type:
            queryset = queryset.filter(
                reference_type=reference_type
            )

        if start_date:
            queryset = queryset.filter(
                created_at__date__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                created_at__date__lte=end_date
            )

        return queryset.order_by(
            "created_at",
            "id",
        )

    @classmethod
    def summary(
        cls,
        organization,
        product=None,
        warehouse=None,
        location=None,
        start_date=None,
        end_date=None,
    ):
        movements = cls.list(
            organization=organization,
            product=product,
            warehouse=warehouse,
            location=location,
            start_date=start_date,
            end_date=end_date,
        )

        positive = movements.filter(
            quantity__gt=0
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        negative = movements.filter(
            quantity__lt=0
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        return {
            "total_in": positive,
            "total_out": abs(negative),
            "net_movement": positive + negative,
            "movement_count": movements.count(),
        }

    @classmethod
    def running_balance(
        cls,
        organization,
        product,
        warehouse,
        location=None,
        start_date=None,
        end_date=None,
    ):
        movements = cls.list(
            organization=organization,
            product=product,
            warehouse=warehouse,
            location=location,
            start_date=start_date,
            end_date=end_date,
        )

        balance = 0

        results = []

        for movement in movements:
            balance += movement.quantity

            results.append({
                "movement_id": movement.id,
                "created_at": movement.created_at,
                "movement_type": movement.movement_type,
                "reference_type": movement.reference_type,
                "reference_id": movement.reference_id,
                "quantity": movement.quantity,
                "running_balance": balance,
                "notes": movement.notes,
            })

        return results

    @classmethod
    def warehouse_summary(cls, organization, warehouse):
        movements = StockMovement.objects.filter(
            organization=organization,
            warehouse=warehouse,
        )

        positive = movements.filter(
            quantity__gt=0
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        negative = movements.filter(
            quantity__lt=0
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        return {
            "warehouse_id": warehouse.id,
            "total_received": positive,
            "total_issued": abs(negative),
            "net_movement": positive + negative,
            "movement_count": movements.count(),
        }

