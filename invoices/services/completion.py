from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from core.exceptions import BusinessRuleError, InsufficientStockError, WarehouseOrganizationMismatch
from inventory.models import StockMovement
from inventory.services import StockService
from invoices.models import Invoice, ActivityLog


class InvoiceCompletionService:

    @staticmethod
    @transaction.atomic
    def complete(invoice, user=None):
        """
        Atomically complete an invoice and issue stock movements for stockable items.
        """
        # 1. Validate status
        if invoice.status == 'COMPLETED':
            raise BusinessRuleError("This invoice has already been completed.")
        if invoice.status == 'CANCELLED':
            raise BusinessRuleError("Cancelled invoices cannot be completed.")

        # 2. Filter stockable products
        stockable_items = [
            item for item in invoice.items.all()
            if item.product and getattr(item.product, 'is_stockable', True)
        ]

        # 3. Validate warehouse requirement if stockable items exist
        if stockable_items and not invoice.warehouse:
            from inventory.models import Warehouse
            invoice.warehouse = Warehouse.objects.filter(organization=invoice.organization, is_active=True).first()
            if not invoice.warehouse:
                raise BusinessRuleError("A warehouse is required before completing this invoice.")

        if stockable_items and invoice.organization and invoice.warehouse and invoice.warehouse.organization != invoice.organization:
            raise WarehouseOrganizationMismatch()

        # 4. Prevent duplicate stock movements
        duplicate_exists = StockMovement.objects.filter(
            organization=invoice.organization,
            reference_type="INVOICE",
            reference_id=invoice.id,
            movement_type="SALE"
        ).exists()
        if duplicate_exists or invoice.inventory_updated:
            raise BusinessRuleError("This invoice has already generated stock movements.")

        # 5. Lock inventory rows & validate quantities for all stockable items
        for item in stockable_items:
            available = StockService.get_balance(item.product, warehouse=invoice.warehouse)
            required = Decimal(str(item.qty))
            if available < required:
                raise InsufficientStockError(
                    f"Insufficient stock for product '{item.product.name}'. Required: {required}, Available: {available}"
                )

        # 6. Issue stock movements
        for item in stockable_items:
            StockService.issue(
                product=item.product,
                warehouse=invoice.warehouse,
                quantity=Decimal(str(item.qty)),
                reference_type="INVOICE",
                reference_id=invoice.id,
                notes=f"Stock issued for Invoice #{invoice.invoice_no}"
            )

        # 7. Mark invoice completed
        invoice.inventory_updated = True
        invoice.status = 'COMPLETED'
        invoice.save(update_fields=['warehouse', 'inventory_updated', 'status'])

        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            ActivityLog.objects.create(
                user=user,
                action=f"Completed Invoice #{invoice.invoice_no}"
            )

        return invoice

    @staticmethod
    @transaction.atomic
    def cancel(invoice, user=None):
        """
        Atomically cancel an invoice and restore stock via a reversal movement.
        """
        if invoice.status == 'CANCELLED':
            return invoice

        if invoice.inventory_updated and invoice.warehouse:
            stockable_items = [
                item for item in invoice.items.all()
                if item.product and getattr(item.product, 'is_stockable', True)
            ]
            for item in stockable_items:
                StockService.receive(
                    product=item.product,
                    warehouse=invoice.warehouse,
                    quantity=Decimal(str(item.qty)),
                    reference_type="INVOICE_CANCEL",
                    reference_id=invoice.id,
                    notes=f"Stock restored for cancelled Invoice #{invoice.invoice_no}"
                )
            invoice.inventory_updated = False

        invoice.status = 'CANCELLED'
        invoice.save(update_fields=['inventory_updated', 'status'])

        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            ActivityLog.objects.create(
                user=user,
                action=f"Cancelled Invoice #{invoice.invoice_no} and restored stock"
            )

        return invoice
