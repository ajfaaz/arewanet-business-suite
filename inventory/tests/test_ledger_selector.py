from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase

from invoices.models import Organization, Product, ProductCategory

from inventory.models import (
    Warehouse,
    WarehouseLocation,
    StockMovement,
)

from inventory.services import StockService

from inventory.selectors import StockLedgerSelector

from inventory.constants import (
    MOVEMENT_TYPE_OPENING,
    MOVEMENT_TYPE_PURCHASE,
    MOVEMENT_TYPE_SALE,
    MOVEMENT_TYPE_DAMAGE,
)


class StockLedgerSelectorTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Ledger Org A",
            slug="ledger-org-a",
        )

        self.org_b = Organization.objects.create(
            name="Ledger Org B",
            slug="ledger-org-b",
        )

        self.category = ProductCategory.objects.create(
            organization=self.org_a,
            name="Hardware",
        )

        self.product = Product.objects.create(
            organization=self.org_a,
            category=self.category,
            name="Laptop",
            sku="LAP-001",
            selling_price=Decimal("500000.00"),
        )

        self.warehouse = Warehouse.objects.create(
            organization=self.org_a,
            name="Main Warehouse",
            code="MAIN",
        )

        self.location = WarehouseLocation.objects.create(
            warehouse=self.warehouse,
            name="Rack A",
            code="RACK-A",
        )

    def test_list_returns_movements_for_organization(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
        )

        movements = StockLedgerSelector.list(
            organization=self.org_a,
            product=self.product,
            warehouse=self.warehouse,
        )

        self.assertEqual(movements.count(), 1)
        self.assertEqual(
            movements.first().quantity,
            Decimal("100.00"),
        )

    def test_movement_type_filter(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
        )

        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=50,
            movement_type=MOVEMENT_TYPE_PURCHASE,
        )

        opening = StockLedgerSelector.list(
            organization=self.org_a,
            product=self.product,
            movement_type=MOVEMENT_TYPE_OPENING,
        )

        purchases = StockLedgerSelector.list(
            organization=self.org_a,
            product=self.product,
            movement_type=MOVEMENT_TYPE_PURCHASE,
        )

        self.assertEqual(opening.count(), 1)
        self.assertEqual(purchases.count(), 1)

    def test_summary_calculates_in_out_and_net(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
        )

        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=50,
            movement_type=MOVEMENT_TYPE_PURCHASE,
        )

        StockService.issue(
            product=self.product,
            warehouse=self.warehouse,
            quantity=20,
            movement_type=MOVEMENT_TYPE_SALE,
        )

        summary = StockLedgerSelector.summary(
            organization=self.org_a,
            product=self.product,
            warehouse=self.warehouse,
        )

        self.assertEqual(
            summary["total_in"],
            Decimal("150.00"),
        )

        self.assertEqual(
            summary["total_out"],
            Decimal("20.00"),
        )

        self.assertEqual(
            summary["net_movement"],
            Decimal("130.00"),
        )

        self.assertEqual(
            summary["movement_count"],
            3,
        )

    def test_running_balance(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
        )

        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            quantity=50,
            movement_type=MOVEMENT_TYPE_PURCHASE,
        )

        StockService.issue(
            product=self.product,
            warehouse=self.warehouse,
            quantity=20,
            movement_type=MOVEMENT_TYPE_SALE,
        )

        StockService.issue(
            product=self.product,
            warehouse=self.warehouse,
            quantity=5,
            movement_type=MOVEMENT_TYPE_DAMAGE,
        )

        ledger = StockLedgerSelector.running_balance(
            organization=self.org_a,
            product=self.product,
            warehouse=self.warehouse,
        )

        balances = [
            row["running_balance"]
            for row in ledger
        ]

        self.assertEqual(
            balances,
            [
                Decimal("100.00"),
                Decimal("150.00"),
                Decimal("130.00"),
                Decimal("125.00"),
            ],
        )

    def test_ledger_isolation_between_organizations(self):
        movements = StockLedgerSelector.list(
            organization=self.org_b,
            product=self.product,
        )

        self.assertEqual(movements.count(), 0)

    def test_ledger_never_leaks_other_organization_data(self):
        category_b = ProductCategory.objects.create(
            organization=self.org_b,
            name="Hardware",
        )

        product_b = Product.objects.create(
            organization=self.org_b,
            category=category_b,
            name="Server",
            sku="SRV-001",
            selling_price=Decimal("800000.00"),
        )

        warehouse_b = Warehouse.objects.create(
            organization=self.org_b,
            name="B Warehouse",
            code="MAIN",
        )

        StockService.receive(
            product=product_b,
            warehouse=warehouse_b,
            quantity=200,
        )

        result = StockLedgerSelector.list(
            organization=self.org_a,
        )

        self.assertEqual(result.count(), 0)
