from decimal import Decimal
from django.db.models import Sum
from inventory.models import StockMovement


class StockLedgerService:
    """
    Calculates inventory balances from the StockMovement ledger.

    StockMovement is treated as the historical source of truth.
    This service never modifies InventoryItem.
    """

    @classmethod
    def get_balance(cls, product, warehouse, location=None):
        """
        Return the balance represented by the stock ledger.
        """
        movements = StockMovement.objects.filter(
            organization_id=warehouse.organization_id,
            product=product,
            warehouse=warehouse,
            location=location,
        )

        total = movements.aggregate(
            balance=Sum("quantity")
        )["balance"]

        return total if total is not None else Decimal("0.00")

    @classmethod
    def get_product_balance(cls, product, warehouse):
        """
        Return total stock for a product across all locations
        within a warehouse.
        """
        total = StockMovement.objects.filter(
            organization_id=warehouse.organization_id,
            product=product,
            warehouse=warehouse,
        ).aggregate(
            balance=Sum("quantity")
        )["balance"]

        return total if total is not None else Decimal("0.00")

    @classmethod
    def get_movement_count(cls, product, warehouse, location=None):
        return StockMovement.objects.filter(
            organization_id=warehouse.organization_id,
            product=product,
            warehouse=warehouse,
            location=location,
        ).count()
