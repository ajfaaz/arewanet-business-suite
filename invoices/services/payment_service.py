from decimal import Decimal
from datetime import date
from django.db import transaction
from invoices.models import Payment, Invoice
from invoices.services.audit_service import AuditService

class PaymentService:

    @classmethod
    @transaction.atomic
    def record_payment(cls, invoice, amount, payment_method, payment_date=None, notes="", user=None):
        """
        Record a payment against an invoice, update status, and log audit history.
        """
        payment = Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            amount=Decimal(str(amount)),
            payment_method=payment_method,
            payment_date=payment_date or date.today(),
            notes=notes
        )

        # Re-evaluate invoice paid totals & status
        total_paid = sum(p.amount for p in invoice.payments.all())
        if total_paid >= invoice.total_due:
            invoice.status = 'PAID'
        elif total_paid > 0:
            invoice.status = 'PARTIAL'
        invoice.save()

        if user:
            AuditService.log(
                user=user,
                action=f"Recorded payment of ₦{amount:.2f} for Invoice {invoice.invoice_no}",
                reference=invoice.invoice_no
            )

        return payment
