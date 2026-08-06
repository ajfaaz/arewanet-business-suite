from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from core.choices import PaymentStatus, PaymentMethod
from sales.payments.models import Payment, PaymentAllocation
from invoices.models import Invoice


class PaymentSelectors:

    @classmethod
    def get_payment_center_stats(cls, organization):
        today = date.today()
        current_year = today.year
        current_month = today.month

        # Today's Collections
        todays_collections = Payment.objects.filter(
            organization=organization,
            payment_date=today,
            status=PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Monthly Collections
        monthly_collections = Payment.objects.filter(
            organization=organization,
            payment_date__year=current_year,
            payment_date__month=current_month,
            status=PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Outstanding Balance (Open Invoices)
        open_invoices = Invoice.objects.filter(
            organization=organization
        ).exclude(status__in=['PAID', 'CANCELLED', 'DRAFT'])

        outstanding_balance = sum(inv.balance_due for inv in open_invoices)

        # Partial Payments Count
        partial_payments_count = open_invoices.filter(status='PARTIAL').count()

        # Refunds Total
        refunds_total = Payment.objects.filter(
            organization=organization,
            status=PaymentStatus.REFUNDED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Overdue Payments Total
        overdue_invoices = Invoice.objects.filter(
            organization=organization,
            status='OVERDUE'
        )
        overdue_total = sum(inv.balance_due for inv in overdue_invoices)

        return {
            'todays_collections': todays_collections,
            'monthly_collections': monthly_collections,
            'outstanding_balance': outstanding_balance,
            'partial_payments_count': partial_payments_count,
            'refunds_total': refunds_total,
            'overdue_total': overdue_total,
        }

    @classmethod
    def get_payment_analytics(cls, organization):
        method_counts = Payment.objects.filter(
            organization=organization,
            status=PaymentStatus.COMPLETED
        ).values('payment_method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        )

        method_dict = {m[0]: Decimal('0.00') for m in PaymentMethod.choices}
        for item in method_counts:
            method_dict[item['payment_method']] = item['total_amount'] or Decimal('0.00')

        labels = [m[1] for m in PaymentMethod.choices]
        data = [float(method_dict.get(m[0], Decimal('0.00'))) for m in PaymentMethod.choices]

        # Last 6 Months Trend
        today = date.today()
        monthly_trend = []
        for i in range(5, -1, -1):
            target_month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_label = target_month_date.strftime("%b %Y")
            val = Payment.objects.filter(
                organization=organization,
                payment_date__year=target_month_date.year,
                payment_date__month=target_month_date.month,
                status=PaymentStatus.COMPLETED
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            monthly_trend.append({
                'month': month_label,
                'amount': float(val)
            })

        return {
            'method_labels': labels,
            'method_data': data,
            'monthly_trend': monthly_trend,
        }

    @classmethod
    def get_payments_for_timeline(cls, invoice):
        timeline_events = []
        direct_payments = Payment.objects.filter(invoice=invoice)
        for p in direct_payments:
            timeline_events.append({
                'receipt_number': p.receipt_number,
                'amount': p.amount,
                'payment_date': p.payment_date,
                'method': p.get_payment_method_display(),
                'status': p.status,
                'reference': p.reference,
                'notes': p.notes,
            })

        allocations = PaymentAllocation.objects.filter(invoice=invoice).select_related('payment')
        for alloc in allocations:
            p = alloc.payment
            timeline_events.append({
                'receipt_number': p.receipt_number,
                'amount': alloc.amount,
                'payment_date': p.payment_date,
                'method': p.get_payment_method_display(),
                'status': p.status,
                'reference': p.reference,
                'notes': p.notes,
            })

        timeline_events.sort(key=lambda x: x['payment_date'], reverse=True)
        return timeline_events
