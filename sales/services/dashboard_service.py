from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Q

from sales.models import ActivityLog
from invoices.models import Invoice, Payment, Customer, Product, Quotation

class DashboardService:

    @staticmethod
    def statistics(organization=None):
        """
        Compute analytics and KPI statistics for the Sales Dashboard.
        """
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Filters by organization if provided
        inv_qs = Invoice.objects.filter(organization=organization) if organization else Invoice.objects.all()
        pay_qs = Payment.objects.filter(invoice__organization=organization) if organization else Payment.objects.all()
        cust_qs = Customer.objects.filter(organization=organization) if organization else Customer.objects.all()
        prod_qs = Product.objects.filter(organization=organization) if organization else Product.objects.all()
        qtn_qs = Quotation.objects.filter(organization=organization) if organization else Quotation.objects.all()
        act_qs = ActivityLog.objects.all().order_by('-id')[:10]

        # Financial Calculations
        pay_qs = Payment.objects.filter(
            Q(organization=organization) | Q(invoice__organization=organization)
        ).distinct() if organization else Payment.objects.all()

        revenue_today = pay_qs.filter(payment_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        revenue_month = pay_qs.filter(payment_date__gte=month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_revenue = pay_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_invoiced = inv_qs.exclude(status='CANCELLED').aggregate(total=Sum('total_due'))['total'] or Decimal('0.00')
        inv_paid_sum = Payment.objects.filter(invoice__in=inv_qs).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        outstanding_balance = max(Decimal('0.00'), total_invoiced - inv_paid_sum)

        # Counts
        total_customers = cust_qs.count()
        total_products = prod_qs.count()
        total_invoices = inv_qs.count()
        total_quotations = qtn_qs.count()

        paid_invoices_count = inv_qs.filter(status='PAID').count()
        unpaid_invoices_count = inv_qs.filter(Q(status='UNPAID') | Q(status='PARTIAL') | Q(status='OVERDUE')).count()
        draft_invoices_count = inv_qs.filter(status='DRAFT').count()

        draft_quotations_count = qtn_qs.filter(status='DRAFT').count()
        approved_quotations_count = qtn_qs.filter(status='APPROVED').count()
        expired_quotations_count = qtn_qs.filter(status='EXPIRED').count()

        recent_payments = pay_qs.select_related('invoice', 'invoice__customer').order_by('-payment_date', '-id')[:5]

        return {
            "total_revenue": total_revenue,
            "payments_today": revenue_today,
            "revenue_today": revenue_today,
            "revenue_month": revenue_month,
            "outstanding": outstanding_balance,
            "outstanding_balance": outstanding_balance,
            "total_customers": total_customers,
            "customer_count": total_customers,
            "total_products": total_products,
            "total_invoices": total_invoices,
            "total_quotations": total_quotations,
            "paid_count": paid_invoices_count,
            "paid_invoices_count": paid_invoices_count,
            "unpaid_count": unpaid_invoices_count,
            "unpaid_invoices_count": unpaid_invoices_count,
            "draft_invoices_count": draft_invoices_count,
            "draft_quotations_count": draft_quotations_count,
            "approved_quotations_count": approved_quotations_count,
            "expired_quotations_count": expired_quotations_count,
            "recent_payments": recent_payments,
            "recent_activity": act_qs
        }
