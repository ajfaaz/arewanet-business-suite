from invoices.models import Quotation


class QuotationSelector:

    @staticmethod
    def list(organization):
        return Quotation.objects.filter(
            organization=organization
        ).select_related("customer").prefetch_related("items")
