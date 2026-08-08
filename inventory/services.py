from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum
from core.services.base import BaseService
from core.exceptions import InsufficientStockError, WarehouseOrganizationMismatch
from inventory.models import Warehouse, WarehouseLocation, InventoryItem, StockMovement
from inventory.constants import (
    MOVEMENT_TYPE_OPENING,
    MOVEMENT_TYPE_PURCHASE,
    MOVEMENT_TYPE_SALE,
    MOVEMENT_TYPE_TRANSFER_IN,
    MOVEMENT_TYPE_TRANSFER_OUT,
    MOVEMENT_TYPE_ADJUSTMENT_IN,
    MOVEMENT_TYPE_ADJUSTMENT_OUT,
)


class StockService(BaseService):
    """
    Central domain service for handling all stock operations.
    Rule: StockMovement (ledger) is the source of truth, InventoryItem (balance) is the cache.
    """

    @classmethod
    @transaction.atomic
    def receive(
        cls,
        product,
        warehouse,
        quantity,
        location=None,
        movement_type=MOVEMENT_TYPE_OPENING,
        reference_type="",
        reference_id=None,
        notes="",
    ):
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Receive quantity must be strictly greater than 0.")

        if warehouse.organization_id != product.organization_id:
            raise WarehouseOrganizationMismatch("Warehouse and Product belong to different organizations.")

        if location and location.warehouse_id != warehouse.id:
            raise ValueError("Selected location does not belong to the specified warehouse.")

        org = warehouse.organization

        # 1. Create StockMovement Ledger Entry
        movement = StockMovement.objects.create(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
            quantity=qty,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )

        # 2. Update or Create InventoryItem Balance Cache
        item, created = InventoryItem.objects.select_for_update().get_or_create(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
            defaults={"quantity": qty},
        )
        if not created:
            item.quantity = F("quantity") + qty
            item.save(update_fields=["quantity", "updated_at"])
            item.refresh_from_db()

        return movement

    @classmethod
    @transaction.atomic
    def issue(
        cls,
        product,
        warehouse,
        quantity,
        location=None,
        movement_type=MOVEMENT_TYPE_SALE,
        reference_type="",
        reference_id=None,
        notes="",
        allow_negative=False,
    ):
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Issue quantity must be strictly greater than 0.")

        if warehouse.organization_id != product.organization_id:
            raise WarehouseOrganizationMismatch("Warehouse and Product belong to different organizations.")

        if location and location.warehouse_id != warehouse.id:
            raise ValueError("Selected location does not belong to the specified warehouse.")

        org = warehouse.organization

        item = InventoryItem.objects.select_for_update().filter(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
        ).first()

        current_qty = item.quantity if item else Decimal("0.00")

        if not allow_negative and current_qty < qty:
            raise InsufficientStockError(
                f"Cannot issue {qty} units of '{product.name}'. Available balance in warehouse '{warehouse.code}' is {current_qty}."
            )

        # 1. Create StockMovement Ledger Entry (Negative quantity)
        movement = StockMovement.objects.create(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
            quantity=-qty,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )

        # 2. Update InventoryItem Balance Cache
        if not item:
            item = InventoryItem.objects.create(
                organization=org,
                product=product,
                warehouse=warehouse,
                location=location,
                quantity=-qty,
            )
        else:
            item.quantity = F("quantity") - qty
            item.save(update_fields=["quantity", "updated_at"])
            item.refresh_from_db()

        return movement

    @classmethod
    @transaction.atomic
    def adjust(
        cls,
        product,
        warehouse,
        new_quantity,
        location=None,
        reference_type="",
        reference_id=None,
        notes="",
    ):
        target_qty = Decimal(str(new_quantity))
        if target_qty < 0:
            raise ValueError("Stock adjustment new quantity cannot be negative.")

        if warehouse.organization_id != product.organization_id:
            raise WarehouseOrganizationMismatch("Warehouse and Product belong to different organizations.")

        org = warehouse.organization

        item = InventoryItem.objects.select_for_update().filter(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
        ).first()

        current_qty = item.quantity if item else Decimal("0.00")
        delta = target_qty - current_qty

        if delta == 0:
            return None

        if delta > 0:
            movement_type = MOVEMENT_TYPE_ADJUSTMENT_IN
            movement_qty = delta
        else:
            movement_type = MOVEMENT_TYPE_ADJUSTMENT_OUT
            movement_qty = delta  # negative

        # 1. Create StockMovement Ledger Entry
        movement = StockMovement.objects.create(
            organization=org,
            product=product,
            warehouse=warehouse,
            location=location,
            quantity=movement_qty,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )

        # 2. Update InventoryItem Balance Cache
        if not item:
            item = InventoryItem.objects.create(
                organization=org,
                product=product,
                warehouse=warehouse,
                location=location,
                quantity=target_qty,
            )
        else:
            item.quantity = target_qty
            item.save(update_fields=["quantity", "updated_at"])

        return movement

    @classmethod
    @transaction.atomic
    def transfer(
        cls,
        product,
        from_warehouse,
        to_warehouse,
        quantity,
        from_location=None,
        to_location=None,
        reference_type="",
        reference_id=None,
        notes="",
    ):
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Transfer quantity must be strictly greater than 0.")

        if from_warehouse.organization_id != to_warehouse.organization_id:
            raise WarehouseOrganizationMismatch("Source and Destination warehouses must belong to the same organization.")

        out_notes = f"Transfer to {to_warehouse.code}. {notes}".strip()
        in_notes = f"Transfer from {from_warehouse.code}. {notes}".strip()

        out_movement = cls.issue(
            product=product,
            warehouse=from_warehouse,
            quantity=qty,
            location=from_location,
            movement_type=MOVEMENT_TYPE_TRANSFER_OUT,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=out_notes,
        )

        in_movement = cls.receive(
            product=product,
            warehouse=to_warehouse,
            quantity=qty,
            location=to_location,
            movement_type=MOVEMENT_TYPE_TRANSFER_IN,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=in_notes,
        )

        return out_movement, in_movement

    @classmethod
    def get_balance(cls, product, warehouse=None, location=None):
        qs = InventoryItem.objects.filter(product=product)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        if location:
            qs = qs.filter(location=location)

        total = qs.aggregate(total_qty=Sum("quantity"))["total_qty"]
        return total if total is not None else Decimal("0.00")
