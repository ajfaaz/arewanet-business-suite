from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from core.choices import QuotationStatus
from invoices.models import Quotation, QuotationItem, Invoice, InvoiceItem
from invoices.utils import generate_document_number
from invoices.services.audit_service import AuditService

from core.exceptions.business import InvalidQuotationStatus


class QuotationService:

    @classmethod
    def calculate_totals(cls, items, vat_rate=0, discount=0):
        subtotal = Decimal("0.00")
        for item in items:
            if isinstance(item, dict):
                qty = item.get('qty', item.get('quantity', 1))
                price = item.get('unit_price', Decimal("0.00"))
                disc = item.get('discount', Decimal("0.00"))
                line_total = (Decimal(str(qty)) * Decimal(str(price))) - Decimal(str(disc))
                item['total'] = line_total
            else:
                qty = getattr(item, 'qty', getattr(item, 'quantity', 1))
                price = getattr(item, 'unit_price', Decimal("0.00"))
                disc = getattr(item, 'discount', Decimal("0.00"))
                line_total = (Decimal(str(qty)) * Decimal(str(price))) - Decimal(str(disc))
                item.total = line_total
            subtotal += line_total

        vat_rate_dec = Decimal(str(vat_rate or 0))
        vat_amount = (subtotal * vat_rate_dec) / Decimal("100.00")
        total = subtotal + vat_amount - Decimal(str(discount or 0))
        return subtotal, vat_amount, total

    @classmethod
    @transaction.atomic
    def create(cls, quotation, items, user=None):
        vat = getattr(quotation, 'vat', 0)
        discount = getattr(quotation, 'discount', 0)
        subtotal, vat_amount, total = cls.calculate_totals(items, vat, discount)
        quotation.subtotal = subtotal
        quotation.total = total
        quotation.save()

        for item in items:
            if isinstance(item, dict):
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=item.get('description', ''),
                    qty=item.get('qty', item.get('quantity', 1)),
                    unit_price=item.get('unit_price', Decimal("0.00")),
                    total=item.get('total', Decimal("0.00"))
                )
            else:
                item.quotation = quotation
                item.save()

        ref = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        if user:
            AuditService.log(user, f"Created Quotation {ref}", reference=ref)
        return quotation

    @classmethod
    def create_quotation(cls, quotation, items, user=None):
        return cls.create(quotation, items, user=user)

    @classmethod
    @transaction.atomic
    def update(cls, quotation, items, user=None, deleted_items=None):
        vat = getattr(quotation, 'vat', 0)
        discount = getattr(quotation, 'discount', 0)
        subtotal, vat_amount, total = cls.calculate_totals(items, vat, discount)
        quotation.subtotal = subtotal
        quotation.total = total
        quotation.save()

        saved_item_ids = []
        for item in items:
            item.quotation = quotation
            item.save()
            if item.pk:
                saved_item_ids.append(item.pk)

        if deleted_items:
            for d_item in deleted_items:
                if d_item.pk:
                    d_item.delete()

        quotation.items.exclude(pk__in=saved_item_ids).delete()

        ref = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        if user:
            AuditService.log(user, f"Updated Quotation {ref}", reference=ref)
        return quotation

    @classmethod
    @transaction.atomic
    def approve(cls, quotation, user=None):
        quotation.status = QuotationStatus.APPROVED
        quotation.save()
        ref = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        if user:
            AuditService.log(user, f"Approved Quotation {ref}", reference=ref)
        return quotation

    @classmethod
    @transaction.atomic
    def reject(cls, quotation, user=None):
        quotation.status = QuotationStatus.REJECTED
        quotation.save()
        ref = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        if user:
            AuditService.log(user, f"Rejected Quotation {ref}", reference=ref)
        return quotation

    @classmethod
    @transaction.atomic
    def expire(cls, quotation, user=None):
        quotation.status = QuotationStatus.EXPIRED
        quotation.save()
        ref = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        if user:
            AuditService.log(user, f"Marked Quotation {ref} Expired", reference=ref)
        return quotation

    @classmethod
    @transaction.atomic
    def convert_to_invoice(cls, quotation, user=None):
        """
        1-Click Conversion: Automatically convert approved quotation into an Invoice.
        """
        if str(quotation.status) in [QuotationStatus.REJECTED, QuotationStatus.EXPIRED, QuotationStatus.CONVERTED, "REJECTED", "EXPIRED", "CONVERTED"]:
            raise InvalidQuotationStatus()

        quotation_no = getattr(quotation, 'quotation_no', getattr(quotation, 'document_number', ''))
        valid_until = getattr(quotation, 'valid_until', getattr(quotation, 'due_date', None))
        subtotal = getattr(quotation, 'subtotal', getattr(quotation, 'total', Decimal("0.00")))
        vat = getattr(quotation, 'vat', Decimal("0.00"))
        total = getattr(quotation, 'total', Decimal("0.00"))

        invoice_no = generate_document_number(Invoice, "invoice_no", "ANV")
        due_date = valid_until or (date.today() + timedelta(days=30))

        create_kwargs = {
            'organization': quotation.organization,
            'customer': quotation.customer,
            'invoice_no': invoice_no,
            'invoice_date': date.today(),
            'due_date': due_date,
            'project_name': f"Quotation {quotation_no}",
            'deployment_phase': "Converted from Quotation",
            'subtotal': subtotal,
            'vat': vat,
            'total_due': total,
            'status': "UNPAID",
        }
        if hasattr(Invoice, 'notes') and hasattr(quotation, 'notes'):
            create_kwargs['notes'] = quotation.notes

        invoice = Invoice.objects.create(**create_kwargs)

        for q_item in quotation.items.all():
            qty = getattr(q_item, 'qty', getattr(q_item, 'quantity', 1))
            InvoiceItem.objects.create(
                invoice=invoice,
                product=q_item.product,
                description=q_item.description,
                qty=qty,
                unit_price=q_item.unit_price,
                total=q_item.total
            )

        if hasattr(quotation, 'status'):
            if hasattr(quotation, 'quotation_no'):
                quotation.status = "CONVERTED"
            else:
                quotation.status = "APPROVED"
            quotation.save()

        if user:
            AuditService.log(user, f"Converted Quotation {quotation_no} to Invoice {invoice.invoice_no}", reference=invoice.invoice_no)

        return invoice
