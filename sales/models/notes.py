from django.db import models
from django.contrib.auth import get_user_model
from core.models import UUIDModel, TimeStampedModel, AuditModel
from core.choices import CreditNoteStatus, DebitNoteStatus

User = get_user_model()


class CreditNote(UUIDModel, TimeStampedModel, AuditModel, models.Model):
    organization = models.ForeignKey(
        "invoices.Organization",
        on_delete=models.CASCADE,
        related_name="credit_notes"
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="credit_notes"
    )
    customer = models.ForeignKey(
        "invoices.Customer",
        on_delete=models.CASCADE,
        related_name="credit_notes"
    )
    credit_note_no = models.CharField(
        max_length=50,
        unique=True
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=CreditNoteStatus.choices,
        default=CreditNoteStatus.ISSUED
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_credit_notes"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.credit_note_no} - {self.customer.company_name} (₦{self.amount})"


class DebitNote(UUIDModel, TimeStampedModel, AuditModel, models.Model):
    organization = models.ForeignKey(
        "invoices.Organization",
        on_delete=models.CASCADE,
        related_name="debit_notes"
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="debit_notes"
    )
    customer = models.ForeignKey(
        "invoices.Customer",
        on_delete=models.CASCADE,
        related_name="debit_notes"
    )
    debit_note_no = models.CharField(
        max_length=50,
        unique=True
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=DebitNoteStatus.choices,
        default=DebitNoteStatus.ISSUED
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_debit_notes"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.debit_note_no} - {self.customer.company_name} (₦{self.amount})"
