from invoices.models import Product


class ProductSelector:

    @staticmethod
    def list(organization):
        return Product.objects.filter(
            organization=organization
        ).select_related("category", "organization")
