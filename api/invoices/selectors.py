from invoices.models import Invoice


class InvoiceSelector:

    @staticmethod
    def list(organization):
        return Invoice.objects.filter(
            organization=organization
        ).select_related("customer", "organization").prefetch_related("items", "items__product")
