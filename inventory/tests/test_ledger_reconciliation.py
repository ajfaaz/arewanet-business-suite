from decimal import Decimal
from django.test import TestCase

from invoices.models import Organization, Product, ProductCategory
from inventory.models import Warehouse, WarehouseLocation, InventoryItem
from inventory.services import StockService
from inventory.ledger_services import StockLedgerService
from inventory.reconciliation_services import InventoryReconciliationService


class LedgerReconciliationTestCase(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Ledger Test Org",
            slug="ledger-test-org",
        )

        self.category = ProductCategory.objects.create(
            organization=self.organization,
            name="Hardware",
        )

        self.product = Product.objects.create(
            organization=self.organization,
            category=self.category,
            name="Test Router",
            sku="LEDGER-001",
            selling_price=Decimal("100000.00"),
        )

        self.warehouse = Warehouse.objects.create(
            organization=self.organization,
            name="Main Warehouse",
            code="MAIN",
        )

        self.location = WarehouseLocation.objects.create(
            warehouse=self.warehouse,
            name="Rack A",
            code="RACK-A",
        )

    def test_ledger_balance_matches_receive(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
        )

        balance = StockLedgerService.get_balance(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
        )

        self.assertEqual(balance, Decimal("100.00"))

    def test_ledger_balance_matches_receive_and_issue(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
        )

        StockService.issue(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=30,
        )

        balance = StockLedgerService.get_balance(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
        )

        self.assertEqual(balance, Decimal("70.00"))

    def test_reconciliation_passes_for_valid_inventory(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
        )

        item = InventoryItem.objects.get(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
        )

        result = InventoryReconciliationService.reconcile_item(item)

        self.assertTrue(result["is_balanced"])
        self.assertEqual(
            result["ledger_balance"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result["inventory_balance"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result["difference"],
            Decimal("0.00"),
        )

    def test_reconciliation_detects_balance_mismatch(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
        )

        item = InventoryItem.objects.get(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
        )

        item.quantity = Decimal("90.00")
        item.save(update_fields=["quantity"])

        result = InventoryReconciliationService.reconcile_item(item)

        self.assertFalse(result["is_balanced"])
        self.assertEqual(
            result["ledger_balance"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result["inventory_balance"],
            Decimal("90.00"),
        )
        self.assertEqual(
            result["difference"],
            Decimal("10.00"),
        )

    def test_warehouse_reconciliation(self):
        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=50,
        )

        result = InventoryReconciliationService.reconcile_warehouse(
            self.warehouse
        )

        self.assertEqual(result["total_items"], 1)
        self.assertEqual(result["balanced_items"], 1)
        self.assertEqual(result["discrepancies"], [])

    def test_transfer_reconciles_source_and_destination(self):
        destination = Warehouse.objects.create(
            organization=self.organization,
            name="Branch Warehouse",
            code="BRANCH",
        )

        StockService.receive(
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity=100,
        )

        StockService.transfer(
            product=self.product,
            from_warehouse=self.warehouse,
            to_warehouse=destination,
            quantity=40,
            from_location=self.location,
        )

        source_balance = StockLedgerService.get_product_balance(
            self.product,
            self.warehouse,
        )

        destination_balance = StockLedgerService.get_product_balance(
            self.product,
            destination,
        )

        self.assertEqual(source_balance, Decimal("60.00"))
        self.assertEqual(destination_balance, Decimal("40.00"))
