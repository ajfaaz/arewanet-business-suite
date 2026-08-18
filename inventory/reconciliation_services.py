from decimal import Decimal
from inventory.models import InventoryItem
from inventory.ledger_services import StockLedgerService


class InventoryReconciliationService:
    """
    Compares the cached InventoryItem balance against
    the balance derived from StockMovement.
    """

    @classmethod
    def reconcile_item(cls, inventory_item):
        ledger_balance = StockLedgerService.get_balance(
            product=inventory_item.product,
            warehouse=inventory_item.warehouse,
            location=inventory_item.location,
        )

        cached_balance = inventory_item.quantity

        difference = ledger_balance - cached_balance

        return {
            "inventory_item_id": inventory_item.id,
            "product_id": inventory_item.product_id,
            "warehouse_id": inventory_item.warehouse_id,
            "location_id": inventory_item.location_id,
            "ledger_balance": ledger_balance,
            "inventory_balance": cached_balance,
            "difference": difference,
            "is_balanced": difference == Decimal("0.00"),
        }

    @classmethod
    def reconcile_warehouse(cls, warehouse):
        items = InventoryItem.objects.filter(
            organization_id=warehouse.organization_id,
            warehouse=warehouse,
        ).select_related(
            "product",
            "warehouse",
            "location",
        )

        results = [
            cls.reconcile_item(item)
            for item in items
        ]

        return {
            "warehouse_id": warehouse.id,
            "total_items": len(results),
            "balanced_items": sum(
                1 for result in results
                if result["is_balanced"]
            ),
            "discrepancies": [
                result
                for result in results
                if not result["is_balanced"]
            ],
        }
