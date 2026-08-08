from invoices.models import Quotation


class QuotationSelector:

    @staticmethod
    def list(organization):
        return Quotation.objects.filter(
            organization=organization
        ).select_related("customer", "organization").prefetch_related("items", "items__product")
