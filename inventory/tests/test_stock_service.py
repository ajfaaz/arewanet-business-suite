from decimal import Decimal
from django.test import TestCase
from invoices.models import Organization, Product, ProductCategory
from inventory.models import Warehouse, WarehouseLocation, InventoryItem, StockMovement
from inventory.services import StockService
from inventory.selectors import InventorySelector, StockMovementSelector
from inventory.constants import (
    MOVEMENT_TYPE_OPENING,
    MOVEMENT_TYPE_SALE,
    MOVEMENT_TYPE_TRANSFER_IN,
    MOVEMENT_TYPE_TRANSFER_OUT,
    MOVEMENT_TYPE_ADJUSTMENT_IN,
)
from core.exceptions import InsufficientStockError, WarehouseOrganizationMismatch


class StockServiceTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(name="ArewaNet Tech", slug="arewanet-tech")
        self.org_b = Organization.objects.create(name="Delta Networks", slug="delta-networks")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Hardware")
        self.prod_a = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Cisco Router 2901",
            sku="RTR-2901",
            selling_price=Decimal("150000.00")
        )

        self.wh_main = Warehouse.objects.create(organization=self.org_a, name="Main Depot", code="MAIN")
        self.wh_branch = Warehouse.objects.create(organization=self.org_a, name="Branch Depot", code="BRANCH")
        self.loc_rack1 = WarehouseLocation.objects.create(warehouse=self.wh_main, name="Rack 01", code="RACK-01")

        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Delta Central", code="DELTA-WH")

    def test_stock_receive_and_balance_creation(self):
        movement = StockService.receive(
            product=self.prod_a,
            warehouse=self.wh_main,
            quantity=100,
            location=self.loc_rack1,
            movement_type=MOVEMENT_TYPE_OPENING,
            notes="Initial opening stock count"
        )

        self.assertEqual(movement.quantity, Decimal("100.00"))
        self.assertEqual(movement.movement_type, MOVEMENT_TYPE_OPENING)

        balance = StockService.get_balance(self.prod_a, warehouse=self.wh_main, location=self.loc_rack1)
        self.assertEqual(balance, Decimal("100.00"))

    def test_stock_issue_and_insufficient_stock_error(self):
        StockService.receive(product=self.prod_a, warehouse=self.wh_main, quantity=50)

        # Valid Issue
        issue_mv = StockService.issue(product=self.prod_a, warehouse=self.wh_main, quantity=15)
        self.assertEqual(issue_mv.quantity, Decimal("-15.00"))
        self.assertEqual(issue_mv.movement_type, MOVEMENT_TYPE_SALE)

        balance = StockService.get_balance(self.prod_a, warehouse=self.wh_main)
        self.assertEqual(balance, Decimal("35.00"))

        # Over-issue attempt raises InsufficientStockError
        with self.assertRaises(InsufficientStockError):
            StockService.issue(product=self.prod_a, warehouse=self.wh_main, quantity=40)

    def test_stock_adjustment(self):
        StockService.receive(product=self.prod_a, warehouse=self.wh_main, quantity=80)

        # Adjust up to 95 (+15)
        StockService.adjust(product=self.prod_a, warehouse=self.wh_main, new_quantity=95, notes="Found extra items")
        self.assertEqual(StockService.get_balance(self.prod_a, warehouse=self.wh_main), Decimal("95.00"))

        # Adjust down to 90 (-5)
        StockService.adjust(product=self.prod_a, warehouse=self.wh_main, new_quantity=90, notes="Minor audit deduction")
        self.assertEqual(StockService.get_balance(self.prod_a, warehouse=self.wh_main), Decimal("90.00"))

    def test_inter_warehouse_stock_transfer(self):
        StockService.receive(product=self.prod_a, warehouse=self.wh_main, quantity=100)

        out_mv, in_mv = StockService.transfer(
            product=self.prod_a,
            from_warehouse=self.wh_main,
            to_warehouse=self.wh_branch,
            quantity=30
        )

        self.assertEqual(out_mv.movement_type, MOVEMENT_TYPE_TRANSFER_OUT)
        self.assertEqual(in_mv.movement_type, MOVEMENT_TYPE_TRANSFER_IN)

        self.assertEqual(StockService.get_balance(self.prod_a, warehouse=self.wh_main), Decimal("70.00"))
        self.assertEqual(StockService.get_balance(self.prod_a, warehouse=self.wh_branch), Decimal("30.00"))

    def test_cross_organization_security_validation(self):
        with self.assertRaises(WarehouseOrganizationMismatch):
            StockService.receive(product=self.prod_a, warehouse=self.wh_b, quantity=10)

    def test_most_important_inventory_ledger_audit_workflow(self):
        """
        Sprint 7.1 Key Rule Test:
        Opening Stock: +100
        Sale: -20
        Adjustment: +5
        Expected Balance: 85
        Verify stock ledger contains all 3 distinct movement records.
        """
        # 1. Opening Stock (+100)
        StockService.receive(
            product=self.prod_a,
            warehouse=self.wh_main,
            quantity=100,
            movement_type=MOVEMENT_TYPE_OPENING,
            notes="Opening Balance"
        )

        # 2. Sale (-20)
        StockService.issue(
            product=self.prod_a,
            warehouse=self.wh_main,
            quantity=20,
            movement_type=MOVEMENT_TYPE_SALE,
            reference_type="Invoice",
            reference_id=101
        )

        # 3. Adjustment (+5)
        StockService.adjust(
            product=self.prod_a,
            warehouse=self.wh_main,
            new_quantity=85,
            notes="Physical Count Reconciliation"
        )

        # Verify Cache Balance
        cached_balance = StockService.get_balance(self.prod_a, warehouse=self.wh_main)
        self.assertEqual(cached_balance, Decimal("85.00"))

        # Verify Ledger Source of Truth
        movements = StockMovement.objects.filter(
            organization=self.org_a,
            product=self.prod_a,
            warehouse=self.wh_main
        ).order_by("created_at")

        self.assertEqual(movements.count(), 3)
        self.assertEqual(movements[0].quantity, Decimal("100.00"))
        self.assertEqual(movements[0].movement_type, MOVEMENT_TYPE_OPENING)

        self.assertEqual(movements[1].quantity, Decimal("-20.00"))
        self.assertEqual(movements[1].movement_type, MOVEMENT_TYPE_SALE)
        self.assertEqual(movements[1].reference_type, "Invoice")

        self.assertEqual(movements[2].quantity, Decimal("5.00"))
        self.assertEqual(movements[2].movement_type, MOVEMENT_TYPE_ADJUSTMENT_IN)
