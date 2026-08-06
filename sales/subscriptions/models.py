from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from core.models import UUIDModel, TimeStampedModel, AuditModel
from core.choices import BillingCycle, SubscriptionStatus
from invoices.models import Organization, Customer, Product

User = get_user_model()


class SubscriptionTemplate(UUIDModel, TimeStampedModel, AuditModel, models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription_templates"
    )
    title = models.CharField(max_length=255)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.get_billing_cycle_display()})"


class SubscriptionTemplateItem(models.Model):
    template = models.ForeignKey(
        SubscriptionTemplate,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.CharField(max_length=255)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    @property
    def total(self):
        base = (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))
        return max(Decimal("0.00"), base - (self.discount or Decimal("0")))

    def __str__(self):
        return f"{self.description} (Template: {self.template.title})"


class Subscription(UUIDModel, TimeStampedModel, AuditModel, models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    template = models.ForeignKey(
        SubscriptionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions"
    )
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )
    next_invoice_date = models.DateField()
    auto_generate = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.customer.company_name} ({self.get_billing_cycle_display()})"

    @property
    def total_amount(self):
        return sum((item.total for item in self.items.all()), Decimal("0.00"))

    @property
    def mrr(self):
        total = self.total_amount
        if self.status != SubscriptionStatus.ACTIVE:
            return Decimal("0.00")

        if self.billing_cycle == BillingCycle.WEEKLY:
            return total * Decimal("4.33")
        elif self.billing_cycle == BillingCycle.MONTHLY:
            return total
        elif self.billing_cycle == BillingCycle.QUARTERLY:
            return total / Decimal("3.0")
        elif self.billing_cycle == BillingCycle.SEMI_ANNUAL:
            return total / Decimal("6.0")
        elif self.billing_cycle == BillingCycle.ANNUAL:
            return total / Decimal("12.0")
        return total

    @property
    def arr(self):
        return self.mrr * Decimal("12.0")


class SubscriptionItem(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.CharField(max_length=255)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    @property
    def total(self):
        base = (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))
        return max(Decimal("0.00"), base - (self.discount or Decimal("0")))

    def __str__(self):
        return f"{self.description} ({self.subscription.title})"


class SubscriptionLog(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    action = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subscription.title} - {self.action} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"
