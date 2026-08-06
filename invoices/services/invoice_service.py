from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from invoices.models import Invoice, InvoiceItem
from invoices.services.audit_service import AuditService

class InvoiceService:

    @staticmethod
    def calculate_subtotal(items):
        """
        Calculate total amount across invoice items.
        `items` can be a list of InvoiceItem objects or item dicts.
        """
        subtotal = Decimal("0.00")
        for item in items:
            qty = getattr(item, 'qty', 0) if hasattr(item, 'qty') else item.get('qty', 0)
            unit_price = getattr(item, 'unit_price', Decimal("0.00")) if hasattr(item, 'unit_price') else Decimal(str(item.get('unit_price', "0.00")))
            line_total = Decimal(str(qty)) * Decimal(str(unit_price))
            if hasattr(item, 'total'):
                item.total = line_total
            subtotal += line_total
        return subtotal

    @staticmethod
    def calculate_vat(subtotal, vat_rate):
        """
        Calculate VAT amount given a subtotal and percentage rate.
        """
        rate = Decimal(str(vat_rate or 0))
        return (subtotal * rate) / Decimal("100.00")

    @staticmethod
    def calculate_total(subtotal, vat_amount):
        """
        Calculate grand total due.
        """
        return subtotal + vat_amount

    @staticmethod
    def validate_invoice(invoice, items):
        """
        Validate invoice and line items business rules.
        """
        if not invoice.customer_id and not hasattr(invoice, 'customer'):
            raise ValidationError("A customer must be assigned to the invoice.")

        if invoice.due_date and invoice.invoice_date and invoice.due_date < invoice.invoice_date:
            raise ValidationError("Due date cannot be earlier than invoice date.")

        if not items or len(items) == 0:
            raise ValidationError("Invoice must contain at least one line item.")

        for item in items:
            qty = getattr(item, 'qty', 0)
            unit_price = getattr(item, 'unit_price', Decimal("0.00"))
            if qty <= 0:
                raise ValidationError("Item quantity must be greater than zero.")
            if unit_price < 0:
                raise ValidationError("Item unit price cannot be negative.")

    @classmethod
    @transaction.atomic
    def create_invoice(cls, invoice, items, user=None):
        """
        Atomically create invoice, compute totals, save items, and log audit history.
        """
        cls.validate_invoice(invoice, items)

        subtotal = cls.calculate_subtotal(items)
        vat_amount = cls.calculate_vat(subtotal, invoice.vat)
        total_due = cls.calculate_total(subtotal, vat_amount)

        invoice.subtotal = subtotal
        invoice.total_due = total_due
        invoice.save()

        for item in items:
            item.invoice = invoice
            line_qty = getattr(item, 'qty', 0)
            line_price = getattr(item, 'unit_price', Decimal("0.00"))
            item.total = Decimal(str(line_qty)) * Decimal(str(line_price))
            item.save()

        if user:
            AuditService.log(
                user=user,
                action=f"Created Invoice {invoice.invoice_no}",
                reference=invoice.invoice_no
            )

        return invoice

    @classmethod
    @transaction.atomic
    def update_invoice(cls, invoice, items, user=None, deleted_items=None):
        """
        Atomically update an existing invoice and its line items.
        """
        cls.validate_invoice(invoice, items)

        subtotal = cls.calculate_subtotal(items)
        vat_amount = cls.calculate_vat(subtotal, invoice.vat)
        total_due = cls.calculate_total(subtotal, vat_amount)

        invoice.subtotal = subtotal
        invoice.total_due = total_due
        invoice.save()

        saved_item_ids = []
        for item in items:
            item.invoice = invoice
            line_qty = getattr(item, 'qty', 0)
            line_price = getattr(item, 'unit_price', Decimal("0.00"))
            item.total = Decimal(str(line_qty)) * Decimal(str(line_price))
            item.save()
            if item.pk:
                saved_item_ids.append(item.pk)

        if deleted_items:
            for d_item in deleted_items:
                if d_item.pk:
                    d_item.delete()

        # Delete any items belonging to this invoice that were removed/deleted
        invoice.items.exclude(pk__in=saved_item_ids).delete()

        if user:
            AuditService.log(
                user=user,
                action=f"Updated Invoice {invoice.invoice_no}",
                reference=invoice.invoice_no
            )

        return invoice
