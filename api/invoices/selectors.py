from invoices.models import Invoice


class InvoiceSelector:

    @staticmethod
    def list(organization):
        return Invoice.objects.filter(
            organization=organization
        ).select_related("customer").prefetch_related("items")
