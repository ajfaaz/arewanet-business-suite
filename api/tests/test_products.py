from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, UserProfile

User = get_user_model()


class ProductAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="prodadmin", password="password")
        self.org = Organization.objects.create(name="Product Test Org", slug="prod-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Hardware",
            description="Computing Hardware"
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            name="Dell Laptop Inspiron",
            sku="SKU-DELL-001",
            selling_price=Decimal("450000.00"),
            product_type="PRODUCT",
            active=True
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_product(self):
        response = self.client.post("/api/v1/products/", {
            "name": "HP LaserJet Printer",
            "category": self.category.id,
            "product_type": "PRODUCT",
            "sku": "SKU-HP-002",
            "selling_price": "180000.00",
            "active": True
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "HP LaserJet Printer")

    def test_update_product(self):
        response = self.client.patch(f"/api/v1/products/{self.product.id}/", {
            "selling_price": "480000.00"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["data"]["selling_price"])), Decimal("480000.00"))

    def test_delete_product(self):
        prod = Product.objects.create(
            organization=self.org,
            name="Temporary Cable",
            selling_price=Decimal("5000.00")
        )
        response = self.client.delete(f"/api/v1/products/{prod.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Product.objects.filter(id=prod.id).exists())

    def test_search_products(self):
        response = self.client.get("/api/v1/products/?search=Dell")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["data"]), 0)

    def test_filter_products_by_category(self):
        response = self.client.get(f"/api/v1/products/?category={self.category.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["data"]), 0)

    def test_filter_products_by_is_active(self):
        response = self.client.get("/api/v1/products/?is_active=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ordering_and_pagination(self):
        response = self.client.get("/api/v1/products/?ordering=selling_price&page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_summary(self):
        response = self.client.get(f"/api/v1/products/{self.product.id}/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["product"], "Dell Laptop Inspiron")
        self.assertIn("sold_quantity", response.data["data"])

    def test_product_stock(self):
        response = self.client.get(f"/api/v1/products/{self.product.id}/stock/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available", response.data["data"])
        self.assertIn("reorder_level", response.data["data"])

    def test_organization_isolation(self):
        other_user = User.objects.create_user(username="otheradmin", password="password")
        other_org = Organization.objects.create(name="Other Org", slug="other-org")
        UserProfile.objects.create(user=other_user, organization=other_org, role="ADMIN")

        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/v1/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
