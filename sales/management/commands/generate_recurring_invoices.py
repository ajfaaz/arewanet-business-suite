from datetime import date
from django.core.management.base import BaseCommand
from sales.subscriptions.models import Subscription
from sales.subscriptions.services import SubscriptionService
from core.choices import SubscriptionStatus


class Command(BaseCommand):
    help = "Generates recurring invoices for subscriptions due today or past due."

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(self.style.NOTICE(f"Checking for recurring subscriptions due on or before {today}..."))

        due_subscriptions = Subscription.objects.filter(
            next_invoice_date__lte=today,
            auto_generate=True,
            status=SubscriptionStatus.ACTIVE,
            is_active=True
        ).select_related('customer', 'organization').prefetch_related('items')

        count = 0
        total_generated_value = 0

        for sub in due_subscriptions:
            try:
                inv = SubscriptionService.generate_invoice(sub)
                count += 1
                total_generated_value += inv.total_due
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [+] Invoice #{inv.invoice_no} generated for '{sub.title}' ({sub.customer.company_name}) - NGN {inv.total_due:,.2f}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [-] Failed to generate invoice for Subscription '{sub.title}' (ID: {sub.id}): {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished! Total Invoices Generated: {count} | Total Value: NGN {total_generated_value:,.2f}"
            )
        )
