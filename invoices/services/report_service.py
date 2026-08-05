from decimal import Decimal
from invoices.models import Invoice, Payment

class ReportService:

    @staticmethod
    def get_financial_summary(organization):
        """
        Compute financial dashboard metrics for an organization.
        """
        invoices = Invoice.objects.filter(organization=organization)
        payments = Payment.objects.filter(organization=organization)

        total_revenue = sum(p.amount for p in payments)
        total_invoiced = sum(i.total_due for i in invoices)
        unpaid_invoices = invoices.filter(status='UNPAID')
        total_unpaid = sum(i.balance for i in unpaid_invoices if hasattr(i, 'balance'))

        return {
            'total_revenue': total_revenue,
            'total_invoiced': total_invoiced,
            'total_unpaid': total_unpaid,
            'total_invoices_count': invoices.count(),
            'unpaid_count': unpaid_invoices.count()
        }
