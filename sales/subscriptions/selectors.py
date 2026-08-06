import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q
from sales.subscriptions.models import Subscription, SubscriptionTemplate
from core.choices import SubscriptionStatus, BillingCycle
from sales.subscriptions.services import SubscriptionService


class SubscriptionSelector:

    @classmethod
    def get_subscriptions(cls, organization, query=None, customer_id=None, status=None):
        qs = Subscription.objects.filter(organization=organization).select_related('customer', 'template').prefetch_related('items')
        if query:
            qs = qs.filter(
                Q(title__icontains=query) |
                Q(customer__company_name__icontains=query) |
                Q(notes__icontains=query)
            )
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')

    @classmethod
    def get_customer_subscriptions(cls, customer):
        return Subscription.objects.filter(customer=customer).select_related('template').prefetch_related('items', 'logs').order_by('-created_at')

    @classmethod
    def get_templates(cls, organization):
        return SubscriptionTemplate.objects.filter(organization=organization, is_active=True).prefetch_related('items')

    @classmethod
    def get_revenue_forecast(cls, organization, months=3):
        """
        Calculates expected revenue forecast for upcoming months based on active subscriptions.
        """
        today = date.today()
        active_subs = Subscription.objects.filter(
            organization=organization,
            status=SubscriptionStatus.ACTIVE
        ).prefetch_related('items')

        forecast = []

        for i in range(months):
            # Calculate target month date
            m_year = today.year + (today.month + i - 1) // 12
            m_month = (today.month + i - 1) % 12 + 1
            month_name = calendar.month_name[m_month]

            projected_amount = Decimal("0.00")
            subscriptions_renewing = []

            for sub in active_subs:
                sub_total = sub.total_amount
                curr_date = sub.next_invoice_date
                
                # Project forward up to end of target month
                target_month_start = date(m_year, m_month, 1)
                target_month_end = date(m_year, m_month, calendar.monthrange(m_year, m_month)[1])

                # Advance date until we reach or pass target month
                while curr_date <= target_month_end:
                    if target_month_start <= curr_date <= target_month_end:
                        projected_amount += sub_total
                        subscriptions_renewing.append({
                            'subscription': sub,
                            'date': curr_date,
                            'amount': sub_total,
                        })
                    curr_date = SubscriptionService.next_billing_date(curr_date, sub.billing_cycle)

            forecast.append({
                'year': m_year,
                'month': m_month,
                'month_name': f"{month_name} {m_year}",
                'projected_amount': projected_amount,
                'renewals': subscriptions_renewing,
            })

        return forecast
