from django.db.models import Q
from sales.models import CreditNote, DebitNote


class CreditSelector:

    @classmethod
    def get_credit_notes(cls, organization, query=None, customer_id=None, status=None):
        qs = CreditNote.objects.filter(organization=organization).select_related('customer', 'invoice', 'created_by')
        if query:
            qs = qs.filter(
                Q(credit_note_no__icontains=query) |
                Q(invoice__invoice_no__icontains=query) |
                Q(customer__company_name__icontains=query) |
                Q(reason__icontains=query)
            )
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')

    @classmethod
    def get_debit_notes(cls, organization, query=None, customer_id=None, status=None):
        qs = DebitNote.objects.filter(organization=organization).select_related('customer', 'invoice', 'created_by')
        if query:
            qs = qs.filter(
                Q(debit_note_no__icontains=query) |
                Q(invoice__invoice_no__icontains=query) |
                Q(customer__company_name__icontains=query) |
                Q(reason__icontains=query)
            )
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')
