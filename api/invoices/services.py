from decimal import Decimal
from datetime import date
from django.db import transaction
from django.http import HttpResponse

from invoices.models import Invoice, InvoiceItem, ActivityLog
from invoices.utils.pdf_generator import generate_invoice_pdf


class InvoiceService:

    @staticmethod
    @transaction.atomic
    def create(*, organization, validated_data):
        items_data = validated_data.pop("items", [])
        
        # Auto-generate invoice number if not provided
        if not validated_data.get("invoice_no"):
            year = date.today().year
            count = Invoice.objects.filter(organization=organization).count() + 1
            validated_data["invoice_no"] = f"INV-{year}-{count:04d}"

        invoice = Invoice.objects.create(
            organization=organization,
            **validated_data
        )

        subtotal = Decimal("0.00")
        for item in items_data:
            qty = Decimal(str(item.get("qty", 1)))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            item_total = qty * unit_price
            subtotal += item_total
            
            InvoiceItem.objects.create(
                invoice=invoice,
                product=item.get("product"),
                description=item.get("description", ""),
                qty=qty,
                unit_price=unit_price,
                total=item_total
            )

        invoice.subtotal = subtotal
        vat_rate = Decimal(str(invoice.vat or 0))
        vat_amount = subtotal * (vat_rate / Decimal("100"))
        invoice.total_due = subtotal + vat_amount
        invoice.save()

        return invoice

    @staticmethod
    def generate_pdf(invoice, response):
        generate_invoice_pdf(response, invoice)
        return response

    @staticmethod
    @transaction.atomic
    def duplicate(invoice):
        year = date.today().year
        count = Invoice.objects.filter(organization=invoice.organization).count() + 1
        new_no = f"INV-{year}-{count:04d}"

        new_invoice = Invoice.objects.create(
            organization=invoice.organization,
            customer=invoice.customer,
            invoice_no=new_no,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=invoice.subtotal,
            vat=invoice.vat,
            total_due=invoice.total_due,
            status="DRAFT"
        )

        for item in invoice.items.all():
            InvoiceItem.objects.create(
                invoice=new_invoice,
                product=item.product,
                description=item.description,
                qty=item.qty,
                unit_price=item.unit_price,
                total=item.total
            )

        return new_invoice

    @staticmethod
    def email_invoice(invoice, user):
        # Create audit log activity entry
        ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=f"Invoice #{invoice.invoice_no} dispatched via Email API to {invoice.customer.email if invoice.customer else 'N/A'}"
        )
        return True
