from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from invoices.models import ActivityLog
from sales.models import DebitNote
from core.choices import DebitNoteStatus


class DebitNoteService:

    @classmethod
    def generate_number(cls, organization):
        year = datetime.now().year
        count = DebitNote.objects.filter(organization=organization).count() + 1
        return f"DN-{year}-{count:04d}"

    @classmethod
    @transaction.atomic
    def issue_debit_note(cls, organization, invoice, amount, reason, user=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValidationError("Debit Note amount must be greater than zero.")

        if invoice.organization != organization:
            raise ValidationError("Invoice does not belong to the user's organization.")

        dn_no = cls.generate_number(organization)
        debit_note = DebitNote.objects.create(
            organization=organization,
            invoice=invoice,
            customer=invoice.customer,
            debit_note_no=dn_no,
            amount=amount,
            reason=reason,
            status=DebitNoteStatus.ISSUED,
            created_by=user
        )

        # Recalculate invoice status
        invoice.update_status()

        if user:
            ActivityLog.objects.create(
                user=user,
                action=f"Issued Debit Note {dn_no} for Invoice {invoice.invoice_no} (₦{amount:,.2f})"
            )

        return debit_note

    @classmethod
    @transaction.atomic
    def cancel_debit_note(cls, debit_note, user=None):
        if debit_note.status == DebitNoteStatus.CANCELLED:
            return debit_note

        debit_note.status = DebitNoteStatus.CANCELLED
        debit_note.save()

        # Recalculate invoice status
        debit_note.invoice.update_status()

        if user:
            ActivityLog.objects.create(
                user=user,
                action=f"Cancelled Debit Note {debit_note.debit_note_no}"
            )

        return debit_note
