from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.exceptions import (
    BusinessRuleError,
    InsufficientStockError,
    WarehouseOrganizationMismatch,
    InvalidDocumentStatusError,
)

from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_CANCELLED,
    MOVEMENT_TYPE_PURCHASE_RETURN,
)

from inventory.models import (
    PurchaseReturnDocument,
    PurchaseReturnDocumentItem,
    InventoryItem,
)

from inventory.services import StockService


class PurchaseReturnService:

    @staticmethod
    def _require_permission(user, permission_code):
        if user is None or not user.is_authenticated:
            raise BusinessRuleError("Authentication is required.")
        from invoices.permissions import has_permission
        if not has_permission(user, permission_code):
            raise BusinessRuleError(f"User does not have permission: {permission_code}")

    @classmethod
    def validate(cls, purchase_return):
        errors = []

        if not purchase_return.organization_id:
            errors.append("Purchase return must belong to an organization.")

        if not purchase_return.supplier_id:
            errors.append("Supplier is required.")

        if not purchase_return.warehouse_id:
            errors.append("Warehouse is required.")

        if purchase_return.supplier_id and purchase_return.supplier.organization_id != purchase_return.organization_id:
            errors.append("Supplier does not belong to the purchase return organization.")

        if purchase_return.warehouse_id and purchase_return.warehouse.organization_id != purchase_return.organization_id:
            errors.append("Warehouse does not belong to the purchase return organization.")

        if purchase_return.purchase_order_id:
            if purchase_return.purchase_order.organization_id != purchase_return.organization_id:
                errors.append("Purchase order does not belong to the purchase return organization.")

        items = list(purchase_return.items.select_related("product"))

        if not items:
            errors.append("Purchase return must contain at least one item.")

        seen_products = set()

        for item in items:
            if item.quantity <= 0:
                errors.append(f"Quantity for '{item.product.name}' must be greater than zero.")

            if item.product.organization_id != purchase_return.organization_id:
                errors.append(f"Product '{item.product.name}' does not belong to the organization.")

            if item.product_id in seen_products:
                errors.append(f"Product '{item.product.name}' appears more than once.")

            seen_products.add(item.product_id)

        if errors:
            raise BusinessRuleError("Purchase return validation failed: " + " ".join(errors))

        cls.validate_against_purchase_order(purchase_return)

        return True

    @classmethod
    def check_stock_availability(cls, purchase_return):
        cls.validate(purchase_return)

        shortages = []

        for item in purchase_return.items.select_related("product"):
            available = StockService.get_balance(
                product=item.product,
                warehouse=purchase_return.warehouse,
            )
            required = Decimal(str(item.quantity))

            if available < required:
                shortages.append(
                    f"{item.product.name}: required={required:.2f}, available={available:.2f}"
                )

        if shortages:
            raise InsufficientStockError(
                "Insufficient stock for purchase return: " + "; ".join(shortages)
            )

        return True

    @classmethod
    def check_stock_availability_locked(cls, purchase_return):
        cls.validate(purchase_return)

        shortages = []

        for item in purchase_return.items.select_related("product"):
            inventory_item = (
                InventoryItem.objects
                .select_for_update()
                .filter(
                    organization=purchase_return.organization,
                    product=item.product,
                    warehouse=purchase_return.warehouse,
                    location=None,
                )
                .first()
            )
            available = inventory_item.quantity if inventory_item else Decimal("0.00")
            required = Decimal(str(item.quantity))

            if available < required:
                shortages.append(
                    f"{item.product.name}: required={required:.2f}, available={available:.2f}"
                )

        if shortages:
            raise InsufficientStockError(
                "Insufficient stock for purchase return: " + "; ".join(shortages)
            )

        return True

    @classmethod
    def get_returned_quantity(cls, purchase_order, product):
        return (
            PurchaseReturnDocumentItem.objects
            .filter(
                purchase_return__purchase_order=purchase_order,
                purchase_return__status=DOC_STATUS_COMPLETED,
                product=product,
            )
            .aggregate(total=Sum("quantity"))
            .get("total")
            or Decimal("0.00")
        )

    @classmethod
    def validate_against_purchase_order(cls, purchase_return):
        if not purchase_return.purchase_order_id:
            return True

        po = purchase_return.purchase_order

        for item in purchase_return.items.select_related("product"):
            po_item = po.items.filter(product=item.product).first()

            if not po_item:
                raise BusinessRuleError(
                    f"Product '{item.product.name}' does not exist on the purchase order."
                )

            returned = cls.get_returned_quantity(po, item.product)
            received = Decimal(str(po_item.received_quantity))
            remaining = max(Decimal("0.00"), received - returned)

            if item.quantity > remaining:
                raise BusinessRuleError(
                    f"Cannot return {item.quantity} units of '{item.product.name}'. "
                    f"Returnable quantity is {remaining}."
                )

        return True

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        organization,
        supplier,
        warehouse,
        document_number,
        return_date,
        purchase_order=None,
        created_by=None,
        notes="",
    ):
        if supplier.organization_id != organization.id:
            raise BusinessRuleError("Supplier does not belong to this organization.")

        if warehouse.organization_id != organization.id:
            raise WarehouseOrganizationMismatch("Warehouse does not belong to this organization.")

        if purchase_order and purchase_order.organization_id != organization.id:
            raise BusinessRuleError("Purchase order does not belong to this organization.")

        return PurchaseReturnDocument.objects.create(
            organization=organization,
            supplier=supplier,
            warehouse=warehouse,
            document_number=document_number,
            return_date=return_date,
            purchase_order=purchase_order,
            created_by=created_by,
            notes=notes,
            status=DOC_STATUS_DRAFT,
        )

    @classmethod
    @transaction.atomic
    def add_item(
        cls,
        *,
        purchase_return,
        product,
        quantity,
        reason="",
    ):
        if purchase_return.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Items can only be added to DRAFT documents.")

        if product.organization_id != purchase_return.organization_id:
            raise BusinessRuleError("Product does not belong to the organization.")

        return PurchaseReturnDocumentItem.objects.create(
            purchase_return=purchase_return,
            product=product,
            quantity=Decimal(str(quantity)),
            reason=reason,
        )

    @classmethod
    def submit(cls, purchase_return):
        if purchase_return.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Only DRAFT documents can be submitted.")

        cls.validate(purchase_return)
        purchase_return.status = DOC_STATUS_PENDING
        purchase_return.save(update_fields=["status", "updated_at"])
        return purchase_return

    @classmethod
    def approve(cls, purchase_return, approved_by):
        cls._require_permission(approved_by, "purchase_return.approve")

        if purchase_return.status not in (DOC_STATUS_DRAFT, DOC_STATUS_PENDING):
            raise InvalidDocumentStatusError("Only DRAFT or PENDING documents can be approved.")

        if purchase_return.created_by_id and purchase_return.created_by_id == approved_by.id:
            raise BusinessRuleError("The user who created this purchase return cannot approve it.")

        cls.check_stock_availability(purchase_return)

        purchase_return.status = DOC_STATUS_APPROVED
        purchase_return.approved_by = approved_by
        purchase_return.approved_at = timezone.now()
        purchase_return.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return purchase_return

    @classmethod
    @transaction.atomic
    def complete(cls, purchase_return, completed_by):
        cls._require_permission(completed_by, "purchase_return.approve")

        if purchase_return.status != DOC_STATUS_APPROVED:
            raise InvalidDocumentStatusError("Only approved purchase returns can be completed.")

        cls.check_stock_availability_locked(purchase_return)

        movements = []

        for item in purchase_return.items.select_related("product"):
            movement = StockService.issue(
                product=item.product,
                warehouse=purchase_return.warehouse,
                quantity=item.quantity,
                movement_type=MOVEMENT_TYPE_PURCHASE_RETURN,
                reference_type="PURCHASE_RETURN",
                reference_id=purchase_return.id,
                notes=f"Purchase return {purchase_return.document_number}",
            )
            movements.append(movement)

        purchase_return.status = DOC_STATUS_COMPLETED
        purchase_return.completed_by = completed_by
        purchase_return.completed_at = timezone.now()
        purchase_return.save(
            update_fields=[
                "status",
                "completed_by",
                "completed_at",
                "updated_at",
            ]
        )

        return purchase_return, movements

    @classmethod
    def cancel(cls, purchase_return):
        if purchase_return.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("Cannot cancel an already COMPLETED purchase return.")

        purchase_return.status = DOC_STATUS_CANCELLED
        purchase_return.save(update_fields=["status", "updated_at"])
        return purchase_return
