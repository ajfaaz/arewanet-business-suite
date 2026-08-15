from decimal import Decimal
from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField
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

    def get_recent_activity(self, limit=5):
        recent_invoices = Invoice.objects.filter(organization=self.organization).select_related('customer').order_by('-invoice_date', '-id')[:limit]
        recent_quotations = Quotation.objects.filter(organization=self.organization).select_related('customer').order_by('-quotation_date', '-id')[:limit]
        recent_payments = Payment.objects.filter(organization=self.organization).select_related('invoice', 'invoice__customer').order_by('-payment_date', '-id')[:limit]

        return {
            'invoices': recent_invoices,
            'quotations': recent_quotations,
            'payments': recent_payments,
        }

    def get_dashboard_data(self, membership=None):
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

        return {
            'kpis': kpis,
            'recent_activity': self.get_recent_activity(),
        }
