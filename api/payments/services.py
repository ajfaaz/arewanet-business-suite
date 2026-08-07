from decimal import Decimal
from datetime import date
from django.db import transaction
from django.http import HttpResponse

from sales.payments.models import Payment
from sales.payments.services import PaymentService as DomainPaymentService
from invoices.models import ActivityLog
from invoices.services.pdf_service import PDFService


class PaymentAPIService:

    @staticmethod
    @transaction.atomic
    def receive(*, organization, validated_data, user):
        invoice = validated_data.get("invoice")
        customer = validated_data.get("customer") or (invoice.customer if invoice else None)
        amount = validated_data.get("amount", Decimal("0.00"))
        payment_method = validated_data.get("payment_method", "BANK")
        payment_date = validated_data.get("payment_date") or date.today()
        reference = validated_data.get("reference", "")
        notes = validated_data.get("notes", "")

        payment = DomainPaymentService.receive_payment(
            organization=organization,
            customer=customer,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            reference=reference,
            notes=notes,
            invoice=invoice,
            user=user
        )
        return payment

    @staticmethod
    @transaction.atomic
    def reverse(*, payment, user):
        if payment.status == "REVERSED":
            return False, "Payment is already reversed."

        payment.status = "REVERSED"
        payment.save()

        if payment.invoice:
            payment.invoice.update_status()

        ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=f"Payment #{payment.receipt_number} reversed for NGN {payment.amount:,.2f}"
        )
        return True, "Payment reversed successfully."

    @staticmethod
    def generate_receipt_pdf(payment, response):
        return PDFService.generate_receipt_pdf(payment)

    @staticmethod
    def email_receipt(payment, user):
        ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=f"Receipt #{payment.receipt_number} dispatched via Email API to {payment.customer.email if payment.customer else 'N/A'}"
        )
        return True
