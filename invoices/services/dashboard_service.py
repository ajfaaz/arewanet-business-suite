from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField, Count
from django.db.models.functions import TruncDay
from invoices.models import Customer, Invoice, Quotation, Payment, Product
from purchases.models import Supplier


class DashboardService:

    def __init__(self, organization):
        self.organization = organization

    def _format_currency(self, amount):
        val = amount or Decimal('0.00')
        return f"₦{val:,.2f}"

    def has_permission(self, membership, permission_code):
        if not membership:
            return True
        if hasattr(membership, 'role') and membership.role and membership.role.slug == 'administrator':
            return True
        normalized_code = permission_code.replace('_', '.')
        return membership.has_permission(normalized_code) or membership.has_permission(permission_code)

    def get_date_range(self, period='month'):
        now = timezone.now()
        today = now.date()

        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'year':
            start_date = date(today.year, 1, 1)
            end_date = today
        else:
            # Default: month
            start_date = today.replace(day=1)
            end_date = today

        return start_date, end_date

    def get_customer_count(self):
        return Customer.objects.filter(organization=self.organization).count()

    def get_supplier_count(self):
        return Supplier.objects.filter(organization=self.organization).count()

    def get_product_count(self):
        return Product.objects.filter(organization=self.organization).count()

    def get_customer_kpi(self):
        count = self.get_customer_count()
        return {
            'count': count,
            'formatted_count': f"{count:,}",
        }

    def get_supplier_kpi(self):
        count = self.get_supplier_count()
        return {
            'count': count,
            'formatted_count': f"{count:,}",
        }

    def get_product_kpi(self):
        qs = Product.objects.filter(organization=self.organization)
        total_count = qs.count()

        low_stock_count = qs.filter(
            is_stockable=True
        ).filter(
            Q(reorder_level__gt=0) | Q(minimum_stock__gt=0)
        ).count()

        stock_val_agg = qs.aggregate(
            val=Sum(ExpressionWrapper(F('cost_price'), output_field=DecimalField()))
        )['val'] or Decimal('0.00')

        return {
            'total_count': total_count,
            'low_stock_count': low_stock_count,
            'stock_value_raw': stock_val_agg,
            'stock_value': self._format_currency(stock_val_agg),
        }

    def get_quotation_kpi(self):
        qs = Quotation.objects.filter(organization=self.organization)
        total_count = qs.count()
        pending_count = qs.filter(status__in=['DRAFT', 'SENT']).count()
        converted_count = qs.filter(status='CONVERTED').count()

        return {
            'total_count': total_count,
            'pending_count': pending_count,
            'converted_count': converted_count,
        }

    def get_invoice_kpi(self):
        qs = Invoice.objects.filter(organization=self.organization)
        total_count = qs.count()
        total_invoiced = qs.aggregate(val=Sum('total_due'))['val'] or Decimal('0.00')
        outstanding = qs.filter(status__in=['UNPAID', 'PARTIAL', 'OVERDUE']).aggregate(val=Sum('total_due'))['val'] or Decimal('0.00')
        paid_count = qs.filter(status='PAID').count()
        unpaid_count = qs.filter(status__in=['UNPAID', 'PARTIAL', 'OVERDUE']).count()

        return {
            'total_count': total_count,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'total_invoiced_raw': total_invoiced,
            'total_invoiced': self._format_currency(total_invoiced),
            'outstanding_raw': outstanding,
            'outstanding': self._format_currency(outstanding),
        }

    def get_invoice_summary(self):
        return self.get_invoice_kpi()

    def get_payment_summary(self):
        return self.get_payment_kpi()

    def get_quotation_summary(self):
        return self.get_quotation_kpi()

    def get_recent_invoices(self, limit=5):
        return Invoice.objects.filter(organization=self.organization).select_related('customer').order_by('-invoice_date', '-id')[:limit]

    def get_recent_quotations(self, limit=5):
        return Quotation.objects.filter(organization=self.organization).select_related('customer').order_by('-quotation_date', '-id')[:limit]

    def get_recent_payments(self, limit=5):
        return Payment.objects.filter(organization=self.organization).select_related('invoice', 'invoice__customer').order_by('-payment_date', '-id')[:limit]

    def get_payment_kpi(self):
        qs = Payment.objects.filter(organization=self.organization)
        total_received = qs.aggregate(val=Sum('amount'))['val']
        paid_inv_sum = Invoice.objects.filter(organization=self.organization, status='PAID').aggregate(val=Sum('total_due'))['val'] or Decimal('0.00')

        if not total_received or total_received == 0:
            total_received = paid_inv_sum
        else:
            total_received = max(total_received, paid_inv_sum)

        total_count = max(qs.count(), Invoice.objects.filter(organization=self.organization, status='PAID').count())

        return {
            'total_count': total_count,
            'total_received_raw': total_received,
            'total_received': self._format_currency(total_received),
        }

    def get_sales_trend(self, membership=None, period='month'):
        if not self.has_permission(membership, 'invoice.view'):
            return []

        start_date, end_date = self.get_date_range(period)

        qs = Invoice.objects.filter(
            organization=self.organization,
            invoice_date__gte=start_date,
            invoice_date__lte=end_date
        ).annotate(
            day=TruncDay('invoice_date')
        ).values('day').annotate(
            amount=Sum('total_due'),
            count=Count('id')
        ).order_by('day')

        trend = []
        max_amt = Decimal('0.00')
        for item in qs:
            amt = item['amount'] or Decimal('0.00')
            if amt > max_amt:
                max_amt = amt
            trend.append({
                'date': item['day'].strftime('%d %b') if item['day'] else '',
                'amount_raw': float(amt),
                'amount': self._format_currency(amt),
                'count': item['count'],
            })

        # Calculate percentages for bar height rendering
        if max_amt > 0:
            for t in trend:
                t['height_pct'] = max(10, int((t['amount_raw'] / float(max_amt)) * 100))
        else:
            for t in trend:
                t['height_pct'] = 0

        return trend

    def get_outstanding_receivables(self, membership=None):
        if not self.has_permission(membership, 'invoice.view'):
            return None

        today = timezone.now().date()
        unpaid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status__in=['UNPAID', 'PARTIAL', 'OVERDUE']
        )

        current = Decimal('0.00')
        d1_30 = Decimal('0.00')
        d31_60 = Decimal('0.00')
        d61_90 = Decimal('0.00')
        d90_plus = Decimal('0.00')

        for inv in unpaid_invoices:
            due = inv.total_due or Decimal('0.00')
            if not inv.due_date or inv.due_date >= today:
                current += due
            else:
                days_overdue = (today - inv.due_date).days
                if days_overdue <= 30:
                    d1_30 += due
                elif days_overdue <= 60:
                    d31_60 += due
                elif days_overdue <= 90:
                    d61_90 += due
                else:
                    d90_plus += due

        total_outstanding = current + d1_30 + d31_60 + d61_90 + d90_plus

        return {
            'total_raw': total_outstanding,
            'total': self._format_currency(total_outstanding),
            'current': self._format_currency(current),
            'd1_30': self._format_currency(d1_30),
            'd31_60': self._format_currency(d31_60),
            'd61_90': self._format_currency(d61_90),
            'd90_plus': self._format_currency(d90_plus),
        }

    def get_low_stock_items(self, membership=None, limit=5):
        if not self.has_permission(membership, 'product.view'):
            return []

        qs = Product.objects.filter(
            organization=self.organization,
            is_stockable=True
        ).filter(
            Q(reorder_level__gt=0) | Q(minimum_stock__gt=0)
        )[:limit]

        items = []
        for p in qs:
            items.append({
                'id': p.id,
                'name': p.name,
                'sku': p.sku or 'N/A',
                'reorder_level': p.reorder_level,
                'minimum_stock': p.minimum_stock,
                'unit': p.unit,
            })
        return items

    def get_pending_approvals(self, membership=None):
        pending = {
            'quotations': 0,
            'invoices': 0,
            'grns': 0,
            'gins': 0,
        }

        if self.has_permission(membership, 'quotation.view'):
            pending['quotations'] = Quotation.objects.filter(
                organization=self.organization,
                status='DRAFT'
            ).count()

        if self.has_permission(membership, 'invoice.view'):
            pending['invoices'] = Invoice.objects.filter(
                organization=self.organization,
                status='DRAFT'
            ).count()

        pending['total'] = pending['quotations'] + pending['invoices'] + pending['grns'] + pending['gins']
        return pending

    def get_normalized_activity_timeline(self, membership=None, limit=7):
        timeline = []

        if self.has_permission(membership, 'invoice.view'):
            for inv in Invoice.objects.filter(organization=self.organization).select_related('customer').order_by('-id')[:limit]:
                timeline.append({
                    'type': 'invoice',
                    'icon': 'bi-file-earmark-text text-primary',
                    'title': f"Invoice {inv.invoice_no} created",
                    'reference': inv.invoice_no,
                    'amount': self._format_currency(inv.total_due),
                    'customer': inv.customer.company_name if inv.customer else 'N/A',
                    'date': inv.invoice_date,
                    'url': f"/invoice/{inv.id}/",
                })

        if self.has_permission(membership, 'payment.view'):
            for pay in Payment.objects.filter(organization=self.organization).select_related('invoice', 'invoice__customer').order_by('-id')[:limit]:
                timeline.append({
                    'type': 'payment',
                    'icon': 'bi-cash-stack text-success',
                    'title': f"Payment {getattr(pay, 'reference', None) or pay.id} recorded",
                    'reference': getattr(pay, 'reference', None) or f"PAY-{pay.id}",
                    'amount': self._format_currency(pay.amount),
                    'customer': pay.invoice.customer.company_name if pay.invoice and pay.invoice.customer else 'N/A',
                    'date': pay.payment_date,
                    'url': '/payments/',
                })

        if self.has_permission(membership, 'quotation.view'):
            for q in Quotation.objects.filter(organization=self.organization).select_related('customer').order_by('-id')[:limit]:
                timeline.append({
                    'type': 'quotation',
                    'icon': 'bi-file-earmark-code text-info',
                    'title': f"Quotation {q.quotation_no} generated",
                    'reference': q.quotation_no,
                    'amount': self._format_currency(q.total),
                    'customer': q.customer.company_name if q.customer else 'N/A',
                    'date': q.quotation_date,
                    'url': f"/quotation/{q.id}/",
                })

        # Sort timeline by date descending
        timeline.sort(key=lambda x: x['date'] if x['date'] else timezone.now().date(), reverse=True)
        return timeline[:limit]

    def get_recent_activity(self, limit=5):
        recent_invoices = Invoice.objects.filter(organization=self.organization).select_related('customer').order_by('-invoice_date', '-id')[:limit]
        recent_quotations = Quotation.objects.filter(organization=self.organization).select_related('customer').order_by('-quotation_date', '-id')[:limit]
        recent_payments = Payment.objects.filter(organization=self.organization).select_related('invoice', 'invoice__customer').order_by('-payment_date', '-id')[:limit]

        return {
            'invoices': recent_invoices,
            'quotations': recent_quotations,
            'payments': recent_payments,
        }

    def get_dashboard_data(self, membership=None, period='month'):
        show_customers = self.has_permission(membership, 'customer.view')
        show_suppliers = self.has_permission(membership, 'supplier.view')
        show_products = self.has_permission(membership, 'product.view')
        show_invoices = self.has_permission(membership, 'invoice.view')
        show_payments = self.has_permission(membership, 'payment.view')
        show_quotations = self.has_permission(membership, 'quotation.view')

        kpis = {
            'show_customers': show_customers,
            'show_suppliers': show_suppliers,
            'show_products': show_products,
            'show_invoices': show_invoices,
            'show_payments': show_payments,
            'show_quotations': show_quotations,
        }

        if show_customers:
            kpis['customers'] = self.get_customer_kpi()
        if show_suppliers:
            kpis['suppliers'] = self.get_supplier_kpi()
        if show_products:
            kpis['products'] = self.get_product_kpi()
        if show_invoices:
            kpis['invoices'] = self.get_invoice_kpi()
        if show_payments:
            kpis['payments'] = self.get_payment_kpi()
        if show_quotations:
            kpis['quotations'] = self.get_quotation_kpi()

        actions = {
            'can_create_customer': self.has_permission(membership, 'customer.create'),
            'can_create_quotation': self.has_permission(membership, 'quotation.create'),
            'can_create_invoice': self.has_permission(membership, 'invoice.create'),
            'can_create_grn': self.has_permission(membership, 'grn.create'),
            'can_create_gin': self.has_permission(membership, 'gin.create'),
            'can_create_product': self.has_permission(membership, 'product.create'),
            'can_create_supplier': self.has_permission(membership, 'supplier.create'),
        }

        analytics = {
            'period': period,
            'sales_trend': self.get_sales_trend(membership=membership, period=period),
            'receivables': self.get_outstanding_receivables(membership=membership),
            'low_stock': self.get_low_stock_items(membership=membership),
            'pending_approvals': self.get_pending_approvals(membership=membership),
            'activity_timeline': self.get_normalized_activity_timeline(membership=membership),
        }

        return {
            'kpis': kpis,
            'actions': actions,
            'analytics': analytics,
            'recent_activity': self.get_recent_activity(),
        }
