from decimal import Decimal
from datetime import date
from django.db.models import Q
from invoices.models import Invoice, Customer


class AgingService:

    @classmethod
    def get_aging_summary(cls, organization):
        """
        Computes organization-wide aging breakdown across 0-30, 31-60, 61-90, and 90+ days buckets.
        """
        today = date.today()
        unpaid_invoices = Invoice.objects.filter(
            organization=organization
        ).exclude(status__in=['PAID', 'CANCELLED', 'DRAFT'])

        summary = {
            'current': Decimal('0.00'),       # 0 - 30 days overdue
            'thirty_days': Decimal('0.00'),   # 31 - 60 days overdue
            'sixty_days': Decimal('0.00'),    # 61 - 90 days overdue
            'ninety_days': Decimal('0.00'),   # > 90 days overdue
            'total_outstanding': Decimal('0.00'),
            'total_invoices_count': len(unpaid_invoices),
        }

        customer_aging = {}

        for inv in unpaid_invoices:
            bal = inv.balance_due
            if bal <= 0:
                continue

            days_overdue = 0
            if inv.due_date and inv.due_date < today:
                days_overdue = (today - inv.due_date).days

            if days_overdue <= 30:
                summary['current'] += bal
                bucket_key = 'current'
            elif days_overdue <= 60:
                summary['thirty_days'] += bal
                bucket_key = 'thirty_days'
            elif days_overdue <= 90:
                summary['sixty_days'] += bal
                bucket_key = 'sixty_days'
            else:
                summary['ninety_days'] += bal
                bucket_key = 'ninety_days'

            summary['total_outstanding'] += bal

            # Customer breakdown
            cust_id = inv.customer.id
            if cust_id not in customer_aging:
                customer_aging[cust_id] = {
                    'customer': inv.customer,
                    'current': Decimal('0.00'),
                    'thirty_days': Decimal('0.00'),
                    'sixty_days': Decimal('0.00'),
                    'ninety_days': Decimal('0.00'),
                    'total': Decimal('0.00'),
                    'invoice_count': 0,
                }
            customer_aging[cust_id][bucket_key] += bal
            customer_aging[cust_id]['total'] += bal
            customer_aging[cust_id]['invoice_count'] += 1

        summary['customer_breakdown'] = list(customer_aging.values())
        summary['customer_breakdown'].sort(key=lambda x: x['total'], reverse=True)

        return summary
