from decimal import Decimal
from django.db import IntegrityError, transaction
from django.test import TestCase

from invoices.models import Organization, Product, ProductCategory
from inventory.models import (
    Warehouse,
    WarehouseLocation,
    InventoryItem,
)


class InventoryItemModelTestCase(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Inventory Test Org",
            slug="inventory-test-org",
        )

        self.category = ProductCategory.objects.create(
            organization=self.organization,
            name="General",
        )

        self.product = Product.objects.create(
            organization=self.organization,
            category=self.category,
            name="Test Product",
            sku="TEST-001",
            selling_price=Decimal("100.00"),
        )

        self.warehouse = Warehouse.objects.create(
            organization=self.organization,
            name="Main Warehouse",
            code="MAIN",
        )

    def test_only_one_product_warehouse_balance_without_location(self):
        InventoryItem.objects.create(
            organization=self.organization,
            product=self.product,
            warehouse=self.warehouse,
            location=None,
            quantity=10,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InventoryItem.objects.create(
                    organization=self.organization,
                    product=self.product,
                    warehouse=self.warehouse,
                    location=None,
                    quantity=20,
                )

    def test_same_product_can_have_different_locations(self):
        location_a = WarehouseLocation.objects.create(
            warehouse=self.warehouse,
            name="Rack A",
            code="RACK-A",
        )

        location_b = WarehouseLocation.objects.create(
            warehouse=self.warehouse,
            name="Rack B",
            code="RACK-B",
        )

        InventoryItem.objects.create(
            organization=self.organization,
            product=self.product,
            warehouse=self.warehouse,
            location=location_a,
            quantity=10,
        )

        InventoryItem.objects.create(
            organization=self.organization,
            product=self.product,
            warehouse=self.warehouse,
            location=location_b,
            quantity=20,
        )

        self.assertEqual(
            InventoryItem.objects.filter(
                product=self.product,
                warehouse=self.warehouse,
            ).count(),
            2,
        )
