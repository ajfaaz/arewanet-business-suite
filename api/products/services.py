from invoices.models import Product


class ProductService:

    @staticmethod
    def create(*, organization, validated_data):
        product = Product.objects.create(
            organization=organization,
            **validated_data
        )
        return product
