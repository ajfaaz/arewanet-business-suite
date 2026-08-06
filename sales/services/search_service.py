from django.db.models import Q
from sales.models import Quotation
from invoices.models import Invoice, Payment, Customer, Product

class SearchService:

    @staticmethod
    def global_search(query, organization=None):
        """
        Global search across Invoices, Customers, Products, Quotations, and Payments.
        """
        if not query or not str(query).strip():
            return {
                'invoices': [],
                'customers': [],
                'products': [],
                'quotations': [],
                'payments': [],
                'total_results': 0
            }

        q = str(query).strip()

        inv_qs = Invoice.objects.filter(organization=organization) if organization else Invoice.objects.all()
        cust_qs = Customer.objects.filter(organization=organization) if organization else Customer.objects.all()
        prod_qs = Product.objects.filter(organization=organization) if organization else Product.objects.all()
        qtn_qs = Quotation.objects.filter(organization=organization) if organization else Quotation.objects.all()
        pay_qs = Payment.objects.filter(invoice__organization=organization) if organization else Payment.objects.all()

        invoices = inv_qs.filter(Q(invoice_no__icontains=q) | Q(project_name__icontains=q))[:5]
        customers = cust_qs.filter(Q(company_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))[:5]
        products = prod_qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))[:5]
        quotations = qtn_qs.filter(Q(quotation_no__icontains=q))[:5] if hasattr(Quotation, 'quotation_no') else qtn_qs.filter(Q(document_number__icontains=q))[:5]
        payments = pay_qs.filter(Q(reference__icontains=q))[:5]

        total_results = invoices.count() + customers.count() + products.count() + quotations.count() + payments.count()

        return {
            'invoices': invoices,
            'customers': customers,
            'products': products,
            'quotations': quotations,
            'payments': payments,
            'total_results': total_results
        }
