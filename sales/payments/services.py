from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone
from core.choices import PaymentStatus, PaymentMethod
from sales.payments.models import Payment, PaymentAllocation
from invoices.models import Invoice
from invoices.utils import generate_document_number
from invoices.services.audit_service import AuditService


class PaymentService:

    @classmethod
    def generate_receipt_number(cls):
        return generate_document_number(Payment, "receipt_number", "RCP")

    @classmethod
    @transaction.atomic
    def receive_payment(
        cls,
        organization,
        customer,
        amount,
        payment_method,
        payment_date=None,
        reference="",
        notes="",
        invoice=None,
        allocations=None,
        user=None
    ):
        if not payment_date:
            payment_date = date.today()

        amount_dec = Decimal(str(amount))

        if invoice:
            remaining = invoice.total_due - (invoice.total_paid or Decimal("0.00"))
            if amount_dec > remaining:
                raise ValueError("Payment amount exceeds outstanding invoice balance.")

        receipt_no = cls.generate_receipt_number()

        payment = Payment.objects.create(
            organization=organization,
            customer=customer,
            invoice=invoice,
            receipt_number=receipt_no,
            amount=amount_dec,
            payment_method=payment_method,
            payment_date=payment_date,
            reference=reference,
            notes=notes,
            status=PaymentStatus.COMPLETED,
            created_by=user if user and user.is_authenticated else None
        )

        if invoice:
            invoice.update_status()

        if allocations:
            for item in allocations:
                inv = item['invoice']
                alloc_amount = Decimal(str(item['amount']))
                PaymentAllocation.objects.create(
                    payment=payment,
                    invoice=inv,
                    amount=alloc_amount
                )
                inv.update_status()

        if user and user.is_authenticated:
            target = f"Invoice {invoice.invoice_no}" if invoice else f"Customer {customer.company_name}"
            AuditService.log(
                user,
                f"Received Payment {receipt_no} of ₦{amount_dec:,.2f} ({payment_method}) for {target}",
                reference=receipt_no
            )

        return payment

    @classmethod
    @transaction.atomic
    def reverse_payment(cls, payment, reason="", user=None):
        payment.status = PaymentStatus.REVERSED
        if reason:
            payment.notes = f"{payment.notes}\n[REVERSED: {reason}]".strip()
        payment.save()

        if payment.invoice:
            payment.invoice.update_status()

        for alloc in payment.allocations.all():
            alloc.invoice.update_status()

        if user and user.is_authenticated:
            AuditService.log(
                user,
                f"Reversed Payment {payment.receipt_number} (₦{payment.amount:,.2f})",
                reference=payment.receipt_number
            )
        return payment

    @classmethod
    @transaction.atomic
    def refund_payment(cls, payment, amount=None, reason="", user=None):
        payment.status = PaymentStatus.REFUNDED
        if reason:
            payment.notes = f"{payment.notes}\n[REFUNDED: {reason}]".strip()
        payment.save()

        if payment.invoice:
            payment.invoice.update_status()

        for alloc in payment.allocations.all():
            alloc.invoice.update_status()

        if user and user.is_authenticated:
            AuditService.log(
                user,
                f"Refunded Payment {payment.receipt_number} (₦{payment.amount:,.2f})",
                reference=payment.receipt_number
            )
        return payment

    @classmethod
    @transaction.atomic
    def allocate_multi_invoice_payment(
        cls,
        organization,
        customer,
        amount,
        payment_method,
        payment_date=None,
        selected_invoice_ids=None,
        reference="",
        notes="",
        user=None
    ):
        amount_remaining = Decimal(str(amount))
        invoices_qs = Invoice.objects.filter(
            organization=organization,
            customer=customer
        ).exclude(status__in=['PAID', 'CANCELLED', 'DRAFT']).order_by('due_date', 'id')

        if selected_invoice_ids:
            invoices_qs = invoices_qs.filter(id__in=selected_invoice_ids)

        allocations = []
        for inv in invoices_qs:
            if amount_remaining <= 0:
                break
            due = inv.balance_due
            if due <= 0:
                continue
            alloc_val = min(amount_remaining, due)
            allocations.append({
                'invoice': inv,
                'amount': alloc_val
            })
            amount_remaining -= alloc_val

        primary_invoice = allocations[0]['invoice'] if len(allocations) == 1 else None

        payment = cls.receive_payment(
            organization=organization,
            customer=customer,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            reference=reference,
            notes=notes,
            invoice=primary_invoice,
            allocations=allocations if len(allocations) > 1 or not primary_invoice else None,
            user=user
        )
        return payment

    @classmethod
    def update_invoice_balance(cls, invoice):
        invoice.update_status()
        return invoice.balance_due
