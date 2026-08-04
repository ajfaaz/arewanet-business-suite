from django.db import models


class BaseDocument(models.Model):

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("VIEWED", "Viewed"),
        ("APPROVED", "Approved"),
        ("PARTIAL", "Partially Paid"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
    ]

    organization = models.ForeignKey(
        "invoices.Organization",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set"
    )

    customer = models.ForeignKey(
        "invoices.Customer",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set"
    )

    document_number = models.CharField(
        max_length=50,
        unique=True
    )

    issue_date = models.DateField()

    due_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        abstract = True


class BaseLineItem(models.Model):

    product = models.ForeignKey(
        "invoices.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_set"
    )

    description = models.CharField(
        max_length=255
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        abstract = True
