from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from invoices.models import ActivityLog
from sales.models import CreditNote
from core.choices import CreditNoteStatus


class CreditNoteService:

    @classmethod
    def generate_number(cls, organization):
        year = datetime.now().year
        count = CreditNote.objects.filter(organization=organization).count() + 1
        return f"CN-{year}-{count:04d}"

    @classmethod
    @transaction.atomic
    def issue_credit_note(cls, organization, invoice, amount, reason, user=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValidationError("Credit Note amount must be greater than zero.")

        if invoice.organization != organization:
            raise ValidationError("Invoice does not belong to the user's organization.")

        eff_due = invoice.effective_total_due
        if amount > eff_due:
            raise ValidationError(f"Credit Note amount (₦{amount:,.2f}) cannot exceed effective total due (₦{eff_due:,.2f}).")

        cn_no = cls.generate_number(organization)
        credit_note = CreditNote.objects.create(
            organization=organization,
            invoice=invoice,
            customer=invoice.customer,
            credit_note_no=cn_no,
            amount=amount,
            reason=reason,
            status=CreditNoteStatus.ISSUED,
            created_by=user
        )

        # Recalculate invoice status
        invoice.update_status()

        if user:
            ActivityLog.objects.create(
                user=user,
                action=f"Issued Credit Note {cn_no} for Invoice {invoice.invoice_no} (₦{amount:,.2f})"
            )

        return credit_note

    @classmethod
    @transaction.atomic
    def cancel_credit_note(cls, credit_note, user=None):
        if credit_note.status == CreditNoteStatus.CANCELLED:
            return credit_note

        credit_note.status = CreditNoteStatus.CANCELLED
        credit_note.save()

        # Recalculate invoice status
        credit_note.invoice.update_status()

        if user:
            ActivityLog.objects.create(
                user=user,
                action=f"Cancelled Credit Note {credit_note.credit_note_no}"
            )

        return credit_note
