import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from core.choices import BillingCycle, SubscriptionStatus
from invoices.models import Invoice, InvoiceItem, ActivityLog
from sales.services.numbering import DocumentNumberService
from sales.services.notifications import NotificationService
from sales.subscriptions.models import (
    Subscription,
    SubscriptionItem,
    SubscriptionTemplate,
    SubscriptionLog,
)


class SubscriptionService:

    @classmethod
    def next_billing_date(cls, current_date, billing_cycle):
        """
        Calculate next billing date handling month lengths and leap years.
        """
        if isinstance(current_date, str):
            current_date = datetime.strptime(current_date, "%Y-%m-%d").date()

        if billing_cycle == BillingCycle.WEEKLY:
            return current_date + timedelta(days=7)

        months_to_add = 1
        if billing_cycle == BillingCycle.MONTHLY:
            months_to_add = 1
        elif billing_cycle == BillingCycle.QUARTERLY:
            months_to_add = 3
        elif billing_cycle == BillingCycle.SEMI_ANNUAL:
            months_to_add = 6
        elif billing_cycle == BillingCycle.ANNUAL:
            months_to_add = 12

        new_year = current_date.year + (current_date.month + months_to_add - 1) // 12
        new_month = (current_date.month + months_to_add - 1) % 12 + 1
        max_days = calendar.monthrange(new_year, new_month)[1]
        new_day = min(current_date.day, max_days)

        return date(new_year, new_month, new_day)

    @classmethod
    @transaction.atomic
    def create_subscription(cls, organization, customer, title, start_date, billing_cycle, auto_generate=True, items_data=None, template=None, notes="", user=None):
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        next_date = cls.next_billing_date(start_date, billing_cycle)

        subscription = Subscription.objects.create(
            organization=organization,
            customer=customer,
            template=template,
            title=title,
            start_date=start_date,
            billing_cycle=billing_cycle,
            next_invoice_date=start_date,  # First invoice on start date
            auto_generate=auto_generate,
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
            notes=notes,
            created_by=user
        )

        if items_data:
            for item in items_data:
                SubscriptionItem.objects.create(
                    subscription=subscription,
                    product=item.get("product"),
                    description=item.get("description", "Service Subscription"),
                    qty=Decimal(str(item.get("qty", 1))),
                    unit_price=Decimal(str(item.get("unit_price", 0))),
                    discount=Decimal(str(item.get("discount", 0)))
                )

        SubscriptionLog.objects.create(
            subscription=subscription,
            action="CREATED",
            notes=f"Subscription created. First invoice due {subscription.next_invoice_date}",
            created_by=user
        )

        if user:
            ActivityLog.objects.create(
                user=user,
                action=f"Created Subscription '{subscription.title}' for {customer.company_name}"
            )

        return subscription

    @classmethod
    @transaction.atomic
    def create_from_template(cls, template, customer, start_date, user=None):
        items_data = []
        for item in template.items.all():
            items_data.append({
                "product": item.product,
                "description": item.description,
                "qty": item.qty,
                "unit_price": item.unit_price,
                "discount": item.discount,
            })

        return cls.create_subscription(
            organization=template.organization,
            customer=customer,
            title=f"{template.title} - {customer.company_name}",
            start_date=start_date,
            billing_cycle=template.billing_cycle,
            auto_generate=True,
            items_data=items_data,
            template=template,
            notes=template.description,
            user=user
        )

    @classmethod
    @transaction.atomic
    def generate_invoice(cls, subscription, user=None):
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise ValidationError(f"Cannot generate invoice for subscription in status {subscription.get_status_display()}")

        organization = subscription.organization
        customer = subscription.customer
        items = list(subscription.items.all())

        if not items:
            raise ValidationError("Cannot generate invoice for empty subscription without items.")

        # Generate invoice number
        count = Invoice.objects.filter(organization=organization).count() + 1
        inv_no = f"INV-{date.today().year}-{count:04d}"

        subtotal = sum((item.total for item in items), Decimal("0.00"))

        invoice = Invoice.objects.create(
            organization=organization,
            customer=customer,
            invoice_no=inv_no,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            project_name=f"Recurring: {subscription.title}",
            deployment_phase="Subscription Billing",
            subtotal=subtotal,
            vat=Decimal("0.00"),
            total_due=subtotal,
            status="UNPAID"
        )

        for item in items:
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item.description,
                qty=item.qty,
                unit_price=item.unit_price,
                total=item.total
            )

        # Advance next invoice date
        old_next_date = subscription.next_invoice_date
        subscription.next_invoice_date = cls.next_billing_date(old_next_date, subscription.billing_cycle)
        subscription.save(update_fields=["next_invoice_date"])

        SubscriptionLog.objects.create(
            subscription=subscription,
            action="INVOICE_GENERATED",
            notes=f"Auto-generated Invoice #{inv_no} for ₦{subtotal:,.2f}. Next invoice due {subscription.next_invoice_date}",
            created_by=user
        )

        ActivityLog.objects.create(
            user=user,
            action=f"Auto-generated Invoice #{inv_no} from Subscription '{subscription.title}'"
        )

        NotificationService.send_inapp_notification(
            user=user,
            title="Subscription Invoice Generated",
            message=f"Invoice #{inv_no} for ₦{subtotal:,.2f} generated for {customer.company_name}."
        )

        return invoice

    @classmethod
    @transaction.atomic
    def renew(cls, subscription, user=None):
        return cls.generate_invoice(subscription, user=user)

    @classmethod
    @transaction.atomic
    def pause(cls, subscription, user=None):
        subscription.status = SubscriptionStatus.PAUSED
        subscription.save(update_fields=["status"])

        SubscriptionLog.objects.create(
            subscription=subscription,
            action="PAUSED",
            notes="Subscription paused.",
            created_by=user
        )
        return subscription

    @classmethod
    @transaction.atomic
    def resume(cls, subscription, user=None):
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.save(update_fields=["status"])

        SubscriptionLog.objects.create(
            subscription=subscription,
            action="RESUMED",
            notes="Subscription resumed.",
            created_by=user
        )
        return subscription

    @classmethod
    @transaction.atomic
    def cancel(cls, subscription, user=None):
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.is_active = False
        subscription.save(update_fields=["status", "is_active"])

        SubscriptionLog.objects.create(
            subscription=subscription,
            action="CANCELLED",
            notes="Subscription cancelled.",
            created_by=user
        )
        return subscription

    @classmethod
    def calculate_mrr_arr(cls, organization):
        active_subs = Subscription.objects.filter(
            organization=organization,
            status=SubscriptionStatus.ACTIVE
        ).prefetch_related('items')

        total_mrr = sum((sub.mrr for sub in active_subs), Decimal("0.00"))
        total_arr = total_mrr * Decimal("12.0")

        today = date.today()
        renewals_this_month = active_subs.filter(
            next_invoice_date__year=today.year,
            next_invoice_date__month=today.month
        ).count()

        return {
            "mrr": total_mrr,
            "arr": total_arr,
            "active_count": active_subs.count(),
            "paused_count": Subscription.objects.filter(organization=organization, status=SubscriptionStatus.PAUSED).count(),
            "cancelled_count": Subscription.objects.filter(organization=organization, status=SubscriptionStatus.CANCELLED).count(),
            "renewals_this_month": renewals_this_month,
        }
