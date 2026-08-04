from django.db import models
from .base import BaseDocument, BaseLineItem


class Invoice(BaseDocument):

    payment_reference = models.CharField(
        max_length=255,
        blank=True
    )

    vat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.document_number}"


class InvoiceItem(BaseLineItem):

    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount + self.tax
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.document_number} - {self.description}"


class Quotation(BaseDocument):

    expiry_date = models.DateField(
        null=True,
        blank=True
    )

    accepted = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quotation {self.document_number}"


class QuotationItem(BaseLineItem):

    quotation = models.ForeignKey(
        Quotation,
        related_name="items",
        on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount + self.tax
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quotation.document_number} - {self.description}"


class Payment(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateField()

    payment_method = models.CharField(
        max_length=50
    )

    reference = models.CharField(
        max_length=255,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Payment ₦{self.amount} for {self.invoice.document_number}"
