import uuid
from decimal import Decimal
from django.db import models
from core.models import UUIDModel, TimeStampedModel, AuditModel
from core.choices import PaymentMethod, PaymentStatus


class Payment(
    UUIDModel,
    TimeStampedModel,
    AuditModel,
    models.Model
):

    organization = models.ForeignKey(
        "invoices.Organization",
        on_delete=models.CASCADE,
        related_name="sales_payments",
        null=True,
        blank=True
    )

    customer = models.ForeignKey(
        "invoices.Customer",
        on_delete=models.CASCADE,
        related_name="sales_payments",
        null=True,
        blank=True
    )

    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True
    )



    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices
    )

    payment_date = models.DateField()

    reference = models.CharField(
        max_length=255,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.COMPLETED
    )

    class Meta:
        ordering = ["-payment_date", "-created_at"]

    @property
    def receipt(self):
        return self

    def __str__(self):
        return f"{self.receipt_number} - ₦{self.amount:,.2f} ({self.get_payment_method_display()})"


class PaymentAllocation(TimeStampedModel):

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="payment_allocations"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.payment.receipt_number} -> {self.invoice.invoice_no}: ₦{self.amount:,.2f}"
