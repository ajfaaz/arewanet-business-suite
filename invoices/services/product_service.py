from invoices.models import Product, ProductCategory
from invoices.services.audit_service import AuditService

class ProductService:

    @staticmethod
    def create_product(organization, product_data, user=None):
        """
        Create a product or service under the specified organization.
        """
        product = Product.objects.create(
            organization=organization,
            category=product_data.get('category'),
            product_type=product_data.get('product_type', 'SERVICE'),
            name=product_data.get('name'),
            sku=product_data.get('sku', ''),
            description=product_data.get('description', ''),
            unit=product_data.get('unit', 'Unit'),
            selling_price=product_data.get('selling_price', 0),
            cost_price=product_data.get('cost_price', 0),
            taxable=product_data.get('taxable', True),
            active=product_data.get('active', True)
        )

        if user:
            AuditService.log(
                user=user,
                action=f"Created Product {product.name}",
                reference=product.sku or product.name
            )

        return product
