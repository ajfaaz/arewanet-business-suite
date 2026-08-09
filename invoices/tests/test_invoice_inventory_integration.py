from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, Invoice, InvoiceItem, Customer, UserProfile
from inventory.models import Warehouse, InventoryItem, StockMovement
from inventory.services import StockService
from invoices.services.invoice_service import InvoiceService
from invoices.services.completion import InvoiceCompletionService
from core.exceptions import InsufficientStockError, WarehouseOrganizationMismatch, BusinessRuleError

User = get_user_model()


class SalesInventoryIntegrationTestCase(TestCase):

    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(name="ArewaNet Sales & Logistics", slug="arewanet-sales-logistics")
        self.user_a = User.objects.create_user(username="salesusera", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Electronics")
        self.laptop = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="ThinkPad T14",
            sku="TP-T14",
            selling_price=Decimal("450000.00"),
            is_stockable=True
        )
        self.keyboard = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Mechanical Keyboard",
            sku="KB-MECH",
            selling_price=Decimal("35000.00"),
            is_stockable=True
        )
        self.web_design_service = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Website Design & Consultation",
            sku="SERV-WEB",
            selling_price=Decimal("150000.00"),
            is_stockable=False
        )

        self.wh_a = Warehouse.objects.create(organization=self.org_a, name="Main Warehouse", code="WH-MAIN")

        # Organization B
        self.org_b = Organization.objects.create(name="Sahara Telecoms", slug="sahara-telecoms-sales")
        self.user_b = User.objects.create_user(username="salesuserb", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Sahara Depot", code="WH-SAHARA")

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Northern Systems Ltd",
            email="info@northernsystems.ng",
            phone="08030000000"
        )

        self.client = APIClient()

    def test_1_draft_invoice_does_not_affect_stock(self):
        # Initial Stock = 100
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-001",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # Expected: Stock remains 100
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertFalse(inv.inventory_updated)

    def test_2_completed_invoice_reduces_stock(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-002",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # Complete Invoice
        InvoiceCompletionService.complete(inv)

        # Expected: Stock = 90
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))
        self.assertEqual(inv.status, "COMPLETED")
        self.assertTrue(inv.inventory_updated)

    def test_3_service_item_does_not_generate_stock_movement(self):
        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-003",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        # Service product with is_stockable=False
        InvoiceItem.objects.create(invoice=inv, product=self.web_design_service, qty=Decimal("1.00"), unit_price=self.web_design_service.selling_price)

        InvoiceCompletionService.complete(inv)

        # Expected: Invoice completed, but 0 stock movements generated
        self.assertEqual(inv.status, "COMPLETED")
        movements_count = StockMovement.objects.filter(reference_id=inv.id).count()
        self.assertEqual(movements_count, 0)

    def test_4_insufficient_stock_rejection(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("5.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-004",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        with self.assertRaises(InsufficientStockError):
            InvoiceCompletionService.complete(inv)

        # Stock remains 5 and invoice status remains DRAFT
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("5.00"))
        self.assertEqual(inv.status, "DRAFT")
        self.assertFalse(inv.inventory_updated)

    def test_5_multiple_items_stock_deduction(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))
        StockService.receive(self.keyboard, warehouse=self.wh_a, quantity=Decimal("50.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-005",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)
        InvoiceItem.objects.create(invoice=inv, product=self.keyboard, qty=Decimal("5.00"), unit_price=self.keyboard.selling_price)

        InvoiceCompletionService.complete(inv)

        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))
        self.assertEqual(StockService.get_balance(self.keyboard, warehouse=self.wh_a), Decimal("45.00"))

    def test_6_atomic_rollback_on_single_failing_item(self):
        # Laptop = 100 available, Keyboard = 2 available
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))
        StockService.receive(self.keyboard, warehouse=self.wh_a, quantity=Decimal("2.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-006",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)
        InvoiceItem.objects.create(invoice=inv, product=self.keyboard, qty=Decimal("5.00"), unit_price=self.keyboard.selling_price)

        with self.assertRaises(InsufficientStockError):
            InvoiceCompletionService.complete(inv)

        # Zero partial deduction: Laptop remains 100, Keyboard remains 2
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.keyboard, warehouse=self.wh_a), Decimal("2.00"))

    def test_7_duplicate_completion_protection(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-007",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # First completion
        InvoiceCompletionService.complete(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

        # Second completion attempt must raise BusinessRuleError
        with self.assertRaises(BusinessRuleError):
            InvoiceCompletionService.complete(inv)

        # Stock remains 90 (deducted only ONCE)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

    def test_8_warehouse_organization_isolation(self):
        # Create product_b belonging to Org B and receive stock in Org B's Warehouse
        laptop_b = Product.objects.create(
            organization=self.org_b,
            name="ThinkPad T14 Org B",
            sku="TP-T14-B",
            selling_price=Decimal("450000.00"),
            is_stockable=True
        )
        StockService.receive(laptop_b, warehouse=self.wh_b, quantity=Decimal("100.00"))

        today = timezone.now().date()
        # Invoice belonging to Org A trying to use Org B's Warehouse
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-008",
            customer=self.customer_a,
            warehouse=self.wh_b,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=laptop_b, qty=Decimal("10.00"), unit_price=laptop_b.selling_price)

        with self.assertRaises(WarehouseOrganizationMismatch):
            InvoiceCompletionService.complete(inv)

    def test_9_cancellation_reversal_restores_stock(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-009",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # Complete sale: Stock = 90
        InvoiceCompletionService.complete(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

        # Cancel Invoice: Reversal movement restores stock to 100
        InvoiceCompletionService.cancel(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertEqual(inv.status, "CANCELLED")

        # Verify audit movements preserved (both OUT and IN recorded)
        movements = StockMovement.objects.filter(reference_id=inv.id)
        self.assertEqual(movements.count(), 2)

    def test_10_completed_invoice_editing_blocked(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-010",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        item = InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        InvoiceCompletionService.complete(inv)

        # Attempting to edit completed invoice via InvoiceService.update_invoice must raise BusinessRuleError
        with self.assertRaises(BusinessRuleError):
            InvoiceService.update_invoice(inv, [item])
