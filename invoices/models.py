from django.db import models
from django.db.models import Sum
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .utils import generate_document_number
import uuid
from core.choices import QuotationStatus

class Organization(models.Model):

    name = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        unique=True
    )

    # Branding

    logo = models.ImageField(
        upload_to='organizations/logo/',
        blank=True,
        null=True
    )

    signature = models.ImageField(
        upload_to='organizations/signatures/',
        blank=True,
        null=True
    )

    stamp = models.ImageField(
        upload_to='organizations/stamps/',
        blank=True,
        null=True
    )

    # Contact

    phone = models.CharField(
        max_length=50
    )

    email = models.EmailField()

    website = models.URLField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    # Banking

    bank_name = models.CharField(
        max_length=255,
        blank=True
    )

    account_name = models.CharField(
        max_length=255,
        blank=True
    )

    account_number = models.CharField(
        max_length=50,
        blank=True
    )

    # Invoice Settings

    invoice_prefix = models.CharField(
        max_length=10,
        default='ANV'
    )

    default_vat = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    currency = models.CharField(
        max_length=10,
        default='NGN'
    )

    terms = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name

class Customer(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE     
    )

    company_name = models.CharField(max_length=255)

    contact_person = models.CharField(
        max_length=255,
        blank=True
    )

    email = models.EmailField()

    phone = models.CharField(max_length=20)

    address = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.company_name


class ProductCategory(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "name")

    def __str__(self):
        return self.name


class Product(models.Model):

    PRODUCT_TYPES = (
        ("SERVICE", "Service"),
        ("PRODUCT", "Product"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default="SERVICE"
    )

    name = models.CharField(
        max_length=255
    )

    sku = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    barcode = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    unit = models.CharField(
        max_length=50,
        default="Service"
    )

    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    minimum_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    taxable = models.BooleanField(
        default=True
    )

    active = models.BooleanField(
        default=True
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def price(self):
        return self.selling_price

    @property
    def is_active(self):
        return self.active

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Invoice(models.Model):

    STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
        ('OVERDUE', 'Overdue'),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    invoice_no = models.CharField(
        max_length=50,
        unique=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    public_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,
        unique=True
    )

    payment_reference = models.CharField(
        max_length=255,
        blank=True
    )

    invoice_date = models.DateField()

    due_date = models.DateField()

    project_name = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    deployment_phase = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    vat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def vat_amount(self):
        sub = Decimal(str(self.subtotal or 0))
        rate = Decimal(str(self.vat or 0))
        return (sub * rate) / Decimal('100')

    @property
    def total_paid(self):
        direct_paid = self.payments.exclude(status__in=['REVERSED', 'REFUNDED', 'FAILED']).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        legacy_paid = self.legacy_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        allocated_paid = self.payment_allocations.exclude(payment__status__in=['REVERSED', 'REFUNDED', 'FAILED']).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return direct_paid + legacy_paid + allocated_paid

    @property
    def amount_paid(self):
        return self.total_paid

    @property
    def total_credit_notes(self):
        if not hasattr(self, 'credit_notes'):
            return Decimal('0.00')
        return self.credit_notes.exclude(status='CANCELLED').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def total_debit_notes(self):
        if not hasattr(self, 'debit_notes'):
            return Decimal('0.00')
        return self.debit_notes.exclude(status='CANCELLED').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def effective_total_due(self):
        base_due = self.total_due or Decimal('0.00')
        return max(Decimal('0.00'), base_due + self.total_debit_notes - self.total_credit_notes)

    @property
    def balance(self):
        return max(Decimal('0.00'), self.effective_total_due - self.total_paid)

    @property
    def balance_due(self):
        return self.balance

    @property
    def payment_percentage(self):
        total = float(self.effective_total_due or 0)
        if total == 0:
            return 0.0
        paid = float(self.total_paid)
        return round((paid / total) * 100, 2)

    def update_status(self):
        paid = self.total_paid
        due = self.effective_total_due

        if paid <= 0:
            if self.due_date and self.due_date < date.today() and self.status not in ['DRAFT', 'CANCELLED']:
                new_status = 'OVERDUE'
            else:
                new_status = 'UNPAID'
        elif paid < due:
            new_status = 'PARTIAL'
        else:
            new_status = 'PAID'

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            self.invoice_no = generate_document_number(
                Invoice,
                "invoice_no",
                "ANV",
            )
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "invoice_date"]),
            models.Index(fields=["organization", "due_date"]),
        ]

    def __str__(self):
        return self.invoice_no


class InvoiceItem(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        related_name='items',
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):
        self.total = Decimal(str(self.qty or 0)) * Decimal(str(self.unit_price or 0))

        # Preserve invoice history by copying current product details if not set
        if self.product:
            if not self.description:
                self.description = self.product.name
            if not self.unit_price:
                self.unit_price = self.product.selling_price

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_no}"

class Quotation(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    quotation_no = models.CharField(
        max_length=50,
        unique=True
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )
    quotation_date = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    vat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT
    )
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.quotation_no:
            self.quotation_no = generate_document_number(
                Quotation,
                "quotation_no",
                "QTN",
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.quotation_no


class QuotationItem(models.Model):
    quotation = models.ForeignKey(
        Quotation,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.TextField()
    qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):
        self.total = (Decimal(str(self.qty or 0)) * Decimal(str(self.unit_price or 0))) - Decimal(str(self.discount or 0))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quotation.quotation_no} - {self.description[:20]}"

class Payment(models.Model):

    PAYMENT_METHODS = (
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('POS', 'POS'),
        ('CHEQUE', 'Cheque'),
        ('PAYSTACK', 'Paystack'),
        ('FLUTTERWAVE', 'Flutterwave'),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='legacy_payments'
    )

    reference = models.CharField(
        max_length=120,
        unique=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='BANK'
    )

    payment_date = models.DateField()

    notes = models.TextField(
        blank=True
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    class Meta:
        ordering = ['-payment_date', '-id']

    def clean(self):
        """
        Prevent overpayment.
        """
        super().clean()

        if not self.invoice_id:
            return

        existing = Decimal("0.00")

        if self.pk:
            existing = Payment.objects.exclude(
                pk=self.pk
            ).filter(
                invoice=self.invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")
        else:
            existing = Payment.objects.filter(
                invoice=self.invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")

        due = self.invoice.total_due or Decimal("0.00")
        amt = self.amount or Decimal("0.00")

        if existing + amt > due:
            raise ValidationError(
                "Payment exceeds outstanding balance."
            )

    def __str__(self):
        return self.reference


class Receipt(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='receipt',
        null=True,
        blank=True
    )

    receipt_no = models.CharField(
        max_length=50,
        unique=True
    )

    issued_at = models.DateTimeField(
        default=timezone.now
    )

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = generate_document_number(
                Receipt,
                "receipt_no",
                "RCT",
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_no
    

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('OWNER','Owner'),
        ('ADMIN','Admin'),
        ('ACCOUNTANT','Accountant'),
        ('STAFF','Staff'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='userprofile'
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class ActivityLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    action = models.CharField(
        max_length=255
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"


