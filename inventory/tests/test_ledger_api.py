from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, OrganizationMembership, UserProfile, Role
from inventory.models import Warehouse, WarehouseLocation, StockMovement
from inventory.services import StockService
from inventory.constants import (
    MOVEMENT_TYPE_OPENING,
    MOVEMENT_TYPE_PURCHASE,
    MOVEMENT_TYPE_SALE,
    MOVEMENT_TYPE_DAMAGE,
)


class StockLedgerAPITestCase(APITestCase):

    def setUp(self):
        # User & Organization A
        self.user_a = User.objects.create_user(
            username="user_a",
            password="password123",
        )
        self.org_a = Organization.objects.create(
            name="Org A",
            slug="org-a",
        )
        self.role_a = Role.objects.create(
            name="Admin A",
            slug="admin-a",
        )
        OrganizationMembership.objects.create(
            user=self.user_a,
            organization=self.org_a,
            role=self.role_a,
            is_active=True,
        )
        UserProfile.objects.create(
            user=self.user_a,
            organization=self.org_a,
        )

        self.category_a = ProductCategory.objects.create(
            organization=self.org_a,
            name="Electronics",
        )
        self.product_a = Product.objects.create(
            organization=self.org_a,
            category=self.category_a,
            name="Switch 24P",
            sku="SW-24P",
            selling_price=Decimal("150000.00"),
        )
        self.warehouse_a = Warehouse.objects.create(
            organization=self.org_a,
            name="Depot A",
            code="DEPOT-A",
        )
        self.location_a = WarehouseLocation.objects.create(
            warehouse=self.warehouse_a,
            name="Shelf 1",
            code="SH-1",
        )

        # User & Organization B
        self.user_b = User.objects.create_user(
            username="user_b",
            password="password123",
        )
        self.org_b = Organization.objects.create(
            name="Org B",
            slug="org-b",
        )
        self.role_b = Role.objects.create(
            name="Admin B",
            slug="admin-b",
        )
        OrganizationMembership.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role=self.role_b,
            is_active=True,
        )
        UserProfile.objects.create(
            user=self.user_b,
            organization=self.org_b,
        )

        self.category_b = ProductCategory.objects.create(
            organization=self.org_b,
            name="Servers",
        )
        self.product_b = Product.objects.create(
            organization=self.org_b,
            category=self.category_b,
            name="Rack Server",
            sku="SRV-R1",
            selling_price=Decimal("1200000.00"),
        )
        self.warehouse_b = Warehouse.objects.create(
            organization=self.org_b,
            name="Depot B",
            code="DEPOT-B",
        )

        self.url = reverse("api-stock-ledger")
        self.summary_url = reverse("api-stock-ledger-summary")

    def test_unauthenticated_access_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_list_ledger(self):
        self.client.force_authenticate(user=self.user_a)

        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            location=self.location_a,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
            reference_type="GRN",
            reference_id=1,
            notes="Initial stock",
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)

        result = response.data["results"][0]
        self.assertEqual(result["product_name"], "Switch 24P")
        self.assertEqual(result["product_sku"], "SW-24P")
        self.assertEqual(result["warehouse_name"], "Depot A")
        self.assertEqual(result["location_name"], "Shelf 1")
        self.assertEqual(Decimal(str(result["quantity"])), Decimal("100.00"))
        self.assertEqual(Decimal(str(result["quantity_in"])), Decimal("100.00"))
        self.assertEqual(Decimal(str(result["quantity_out"])), Decimal("0.00"))

    def test_organization_isolation(self):
        # Create movements in Org A and Org B
        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=50,
        )
        StockService.receive(
            product=self.product_b,
            warehouse=self.warehouse_b,
            quantity=200,
        )

        # Authenticated as User A -> sees only Org A movements
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # Authenticated as User B -> sees only Org B movements
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_ledger_filtering(self):
        self.client.force_authenticate(user=self.user_a)

        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            location=self.location_a,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
            reference_type="OPENING",
        )
        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=50,
            movement_type=MOVEMENT_TYPE_PURCHASE,
            reference_type="GRN",
        )
        StockService.issue(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=20,
            movement_type=MOVEMENT_TYPE_SALE,
            reference_type="INVOICE",
        )

        # Filter by movement_type
        res = self.client.get(self.url, {"movement_type": MOVEMENT_TYPE_SALE})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(Decimal(str(res.data["results"][0]["quantity_out"])), Decimal("20.00"))

        # Filter by reference_type
        res = self.client.get(self.url, {"reference_type": "GRN"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

        # Filter by product
        res = self.client.get(self.url, {"product": self.product_a.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

        # Filter by warehouse
        res = self.client.get(self.url, {"warehouse": self.warehouse_a.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

        # Filter by location
        res = self.client.get(self.url, {"location": self.location_a.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

    def test_ledger_pagination(self):
        self.client.force_authenticate(user=self.user_a)

        for i in range(30):
            StockService.receive(
                product=self.product_a,
                warehouse=self.warehouse_a,
                quantity=1,
            )

        res = self.client.get(self.url, {"page": 1, "page_size": 10})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 30)
        self.assertEqual(len(res.data["results"]), 10)
        self.assertIsNotNone(res.data["next"])

    def test_ledger_summary_api(self):
        self.client.force_authenticate(user=self.user_a)

        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
        )
        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=50,
            movement_type=MOVEMENT_TYPE_PURCHASE,
        )
        StockService.issue(
            product=self.product_a,
            warehouse=self.warehouse_a,
            quantity=30,
            movement_type=MOVEMENT_TYPE_SALE,
        )

        res = self.client.get(self.summary_url, {"product": self.product_a.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["total_in"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(res.data["total_out"])), Decimal("30.00"))
        self.assertEqual(Decimal(str(res.data["net_movement"])), Decimal("120.00"))
        self.assertEqual(res.data["movement_count"], 3)
