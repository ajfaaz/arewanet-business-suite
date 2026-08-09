from decimal import Decimal
from django.db import models
from django.conf import settings
from invoices.models import Organization, Product
from inventory.models import Warehouse


class Supplier(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="suppliers"
    )

    code = models.CharField(
        max_length=50
    )

    company_name = models.CharField(
        max_length=255
    )

    contact_person = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    email = models.EmailField(
        blank=True,
        default=""
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )

    address = models.TextField(
        blank=True,
        default=""
    )

    tax_number = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["company_name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.company_name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code and self.organization:
            count = Supplier.objects.filter(organization=self.organization).count() + 1
            self.code = f"SUP-{count:06d}"
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("PARTIAL_RECEIPT", "Partially Received"),
        ("RECEIVED", "Received"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="purchase_orders"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    order_number = models.CharField(
        max_length=50
    )

    order_date = models.DateField()

    expected_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    notes = models.TextField(
        blank=True,
        default=""
    )

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-order_date", "-created_at"]
        unique_together = ("organization", "order_number")

    def __str__(self):
        return f"{self.order_number} - {self.supplier.company_name}"

    def calculate_totals(self):
        sub = Decimal("0.00")
        for item in self.items.all():
            sub += Decimal(str(item.quantity)) * Decimal(str(item.unit_cost))
        self.subtotal = sub
        self.total = sub + Decimal(str(self.tax or 0))
        self.save(update_fields=["subtotal", "total"])


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    received_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    @property
    def remaining_quantity(self):
        return max(Decimal("0.00"), Decimal(str(self.quantity)) - Decimal(str(self.received_quantity)))

    def save(self, *args, **kwargs):
        self.total_cost = Decimal(str(self.quantity)) * Decimal(str(self.unit_cost))
        super().save(*args, **kwargs)
