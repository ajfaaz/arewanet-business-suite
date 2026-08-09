from decimal import Decimal
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from core.exceptions import BusinessRuleError
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem
from invoices.models import ActivityLog


class SupplierService:

    @staticmethod
    @transaction.atomic
    def create_supplier(*, organization, data):
        count = Supplier.objects.filter(organization=organization).count() + 1
        code = data.pop("code", None) or f"SUP-{count:06d}"

        supplier = Supplier.objects.create(
            organization=organization,
            code=code,
            **data
        )
        return supplier

    @staticmethod
    @transaction.atomic
    def update_supplier(*, supplier, data):
        for key, val in data.items():
            setattr(supplier, key, val)
        supplier.save()
        return supplier


class PurchaseService:

    @staticmethod
    @transaction.atomic
    def create_purchase_order(*, organization, supplier, warehouse, items_data, order_date=None, expected_date=None, notes="", user=None):
        if supplier.organization != organization:
            raise BusinessRuleError("Supplier does not belong to the active organization.")
        if warehouse.organization != organization:
            raise BusinessRuleError("Warehouse does not belong to the active organization.")

        year = date.today().year
        count = PurchaseOrder.objects.filter(organization=organization).count() + 1
        order_number = f"PO-{year}-{count:06d}"

        po = PurchaseOrder.objects.create(
            organization=organization,
            supplier=supplier,
            warehouse=warehouse,
            order_number=order_number,
            order_date=order_date or date.today(),
            expected_date=expected_date,
            notes=notes,
            status="DRAFT",
            created_by=user if user and hasattr(user, 'is_authenticated') and user.is_authenticated else None
        )

        subtotal = Decimal("0.00")
        for item in items_data:
            qty = Decimal(str(item.get("quantity", 0)))
            cost = Decimal(str(item.get("unit_cost", 0)))
            if qty <= 0:
                raise ValidationError("Item quantity must be greater than zero.")
            if cost < 0:
                raise ValidationError("Item unit cost cannot be negative.")

            item_total = qty * cost
            subtotal += item_total

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=item.get("product"),
                quantity=qty,
                unit_cost=cost,
                total_cost=item_total
            )

        po.subtotal = subtotal
        po.total = subtotal + Decimal(str(po.tax or 0))
        po.save(update_fields=["subtotal", "total"])

        return po

    @staticmethod
    @transaction.atomic
    def submit_purchase_order(po, user=None):
        if po.status != "DRAFT":
            raise BusinessRuleError("Only DRAFT purchase orders can be submitted.")
        po.status = "SUBMITTED"
        po.save(update_fields=["status"])
        return po

    @staticmethod
    @transaction.atomic
    def approve_purchase_order(po, user=None):
        if po.status not in ["DRAFT", "SUBMITTED"]:
            raise BusinessRuleError("Only DRAFT or SUBMITTED purchase orders can be approved.")
        po.status = "APPROVED"
        po.save(update_fields=["status"])
        return po

    @staticmethod
    @transaction.atomic
    def cancel_purchase_order(po, user=None):
        if po.status in ["RECEIVED", "CLOSED"]:
            raise BusinessRuleError("Received or closed purchase orders cannot be cancelled.")
        po.status = "CANCELLED"
        po.save(update_fields=["status"])
        return po

    @staticmethod
    @transaction.atomic
    def close_purchase_order(po, user=None):
        if po.status == "CANCELLED":
            raise BusinessRuleError("Cancelled purchase orders cannot be closed.")
        po.status = "CLOSED"
        po.save(update_fields=["status"])
        return po
