from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone

from invoices.models import Invoice, InvoiceItem, Customer, Product, Quotation, ActivityLog
from sales.payments.models import Payment
from sales.subscriptions.models import Subscription


class DashboardAPIService:

    @staticmethod
    def get_summary(organization):
        today = date.today()
        month_start = today.replace(day=1)

        pay_qs = Payment.objects.filter(
            Q(organization=organization) | Q(invoice__organization=organization)
        ).exclude(status="REVERSED").distinct() if organization else Payment.objects.exclude(status="REVERSED")

        inv_qs = Invoice.objects.filter(organization=organization) if organization else Invoice.objects.all()
        cust_qs = Customer.objects.filter(organization=organization) if organization else Customer.objects.all()
        prod_qs = Product.objects.filter(organization=organization) if organization else Product.objects.all()
        qtn_qs = Quotation.objects.filter(organization=organization) if organization else Quotation.objects.all()
        sub_qs = Subscription.objects.filter(organization=organization, status="ACTIVE") if organization else Subscription.objects.filter(status="ACTIVE")

        sales_today = pay_qs.filter(payment_date=today).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        sales_this_month = pay_qs.filter(payment_date__gte=month_start).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

        total_invoiced = inv_qs.exclude(status='CANCELLED').aggregate(tot=Sum('total_due'))['tot'] or Decimal('0.00')
        total_paid = pay_qs.aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        outstanding = max(Decimal('0.00'), total_invoiced - total_paid)

        mrr = sub_qs.aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00') if hasattr(Subscription, 'amount') else Decimal('0.00')

        return {
            "sales_today": sales_today,
            "sales_this_month": sales_this_month,
            "revenue": sales_this_month,
            "mrr": mrr,
            "outstanding": outstanding,
            "customers": cust_qs.count(),
            "products": prod_qs.count(),
            "quotations": qtn_qs.count(),
            "invoices": inv_qs.count(),
            "payments": pay_qs.count(),
            "active_subscriptions": sub_qs.count()
        }

    @staticmethod
    def get_revenue_trend(organization):
        today = date.today()
        months_data = []

        for i in range(5, -1, -1):
            # Calculate month date ranges
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            m_start = date(year, month, 1)
            if month == 12:
                m_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(year, month + 1, 1) - timedelta(days=1)

            m_label = m_start.strftime("%b")

            pay_qs = Payment.objects.filter(
                Q(organization=organization) | Q(invoice__organization=organization)
            ).filter(
                payment_date__gte=m_start,
                payment_date__lte=m_end
            ).exclude(status="REVERSED").distinct() if organization else Payment.objects.filter(payment_date__gte=m_start, payment_date__lte=m_end).exclude(status="REVERSED")

            amt = pay_qs.aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
            months_data.append({
                "month": m_label,
                "amount": float(amt)
            })

        return months_data

    @staticmethod
    def get_receivables(organization):
        today = date.today()
        inv_qs = Invoice.objects.filter(organization=organization).exclude(status__in=["PAID", "CANCELLED"]) if organization else Invoice.objects.exclude(status__in=["PAID", "CANCELLED"])

        current = Decimal('0.00')
        days_30 = Decimal('0.00')
        days_60 = Decimal('0.00')
        days_90 = Decimal('0.00')

        for inv in inv_qs:
            balance = inv.balance_due
            if balance <= Decimal('0.00'):
                continue

            days_overdue = (today - inv.due_date).days if inv.due_date else 0

            if days_overdue <= 0:
                current += balance
            elif days_overdue <= 30:
                days_30 += balance
            elif days_overdue <= 60:
                days_60 += balance
            else:
                days_90 += balance

        return {
            "current": current,
            "30_days": days_30,
            "60_days": days_60,
            "90_days": days_90
        }

    @staticmethod
    def get_top_customers(organization):
        pay_qs = Payment.objects.filter(
            Q(organization=organization) | Q(invoice__organization=organization)
        ).exclude(status="REVERSED").values('customer__company_name').annotate(
            revenue=Sum('amount')
        ).order_by('-revenue')[:5] if organization else Payment.objects.exclude(status="REVERSED").values('customer__company_name').annotate(
            revenue=Sum('amount')
        ).order_by('-revenue')[:5]

        results = []
        for row in pay_qs:
            name = row.get('customer__company_name') or "General Customer"
            results.append({
                "name": name,
                "revenue": float(row.get('revenue') or 0)
            })
        return results

    @staticmethod
    def get_top_products(organization):
        items_qs = InvoiceItem.objects.filter(
            invoice__organization=organization
        ).values('product__name').annotate(
            quantity=Sum('qty')
        ).order_by('-quantity')[:5] if organization else InvoiceItem.objects.values('product__name').annotate(
            quantity=Sum('qty')
        ).order_by('-quantity')[:5]

        results = []
        for row in items_qs:
            name = row.get('product__name') or "Standard Item"
            results.append({
                "product": name,
                "quantity": float(row.get('quantity') or 0)
            })
        return results

    @staticmethod
    def get_recent_activity(organization):
        logs = ActivityLog.objects.all().order_by('-created_at')[:10]
        results = []
        now = timezone.now()

        for log in logs:
            action_str = log.action or "Activity performed"
            doc_type = "System"
            if "Invoice" in action_str:
                doc_type = "Invoice"
            elif "Payment" in action_str or "Receipt" in action_str:
                doc_type = "Payment"
            elif "Quotation" in action_str:
                doc_type = "Quotation"
            elif "Customer" in action_str:
                doc_type = "Customer"

            time_diff = now - log.created_at
            if time_diff.seconds < 60 and time_diff.days == 0:
                time_str = "Just now"
            elif time_diff.seconds < 3600 and time_diff.days == 0:
                time_str = f"{time_diff.seconds // 60} minutes ago"
            elif time_diff.days == 0:
                time_str = f"{time_diff.seconds // 3600} hours ago"
            else:
                time_str = f"{time_diff.days} days ago"

            results.append({
                "type": doc_type,
                "message": action_str,
                "time": time_str
            })
        return results

    @staticmethod
    def get_notifications(organization):
        today = date.today()
        inv_qs = Invoice.objects.filter(organization=organization) if organization else Invoice.objects.all()
        qtn_qs = Quotation.objects.filter(organization=organization) if organization else Quotation.objects.all()
        sub_qs = Subscription.objects.filter(organization=organization) if organization else Subscription.objects.all()

        overdue_invoices = inv_qs.filter(status="OVERDUE").count()
        expiring_quotations = qtn_qs.filter(
            valid_until__gte=today,
            valid_until__lte=today + timedelta(days=7),
            status__in=["DRAFT", "SENT"]
        ).count()
        subscriptions_due = sub_qs.filter(
            next_invoice_date__lte=today + timedelta(days=3),
            status="ACTIVE"
        ).count()

        return {
            "overdue_invoices": overdue_invoices,
            "expiring_quotations": expiring_quotations,
            "subscriptions_due": subscriptions_due
        }
