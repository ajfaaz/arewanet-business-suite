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
from core.exceptions import InsufficientStockError, WarehouseOrganizationMismatch

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
            selling_price=Decimal("450000.00")
        )
        self.keyboard = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Mechanical Keyboard",
            sku="KB-MECH",
            selling_price=Decimal("35000.00")
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

    def test_1_completed_invoice_reduces_stock(self):
        # Seed 100 Laptops in WH-MAIN
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))

        # Create Invoice for 10 Laptops
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

        # Complete Invoice
        InvoiceService.complete_invoice(inv)

        # Expected: Stock = 90
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))
        self.assertTrue(inv.inventory_updated)

    def test_2_draft_invoice_does_not_affect_stock(self):
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

        # Draft state must leave stock unchanged at 100
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertFalse(inv.inventory_updated)

    def test_3_insufficient_stock_rejection(self):
        # Seed 5 Laptops
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("5.00"))

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
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # Attempt to complete invoice for 10 Laptops must fail
        with self.assertRaises(InsufficientStockError):
            InvoiceService.complete_invoice(inv)

        # Stock remains 5 and invoice inventory_updated remains False
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("5.00"))
        self.assertFalse(inv.inventory_updated)

    def test_4_multiple_items_stock_deduction(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))
        StockService.receive(self.keyboard, warehouse=self.wh_a, quantity=Decimal("50.00"))

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
        InvoiceItem.objects.create(invoice=inv, product=self.keyboard, qty=Decimal("5.00"), unit_price=self.keyboard.selling_price)

        InvoiceService.complete_invoice(inv)

        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))
        self.assertEqual(StockService.get_balance(self.keyboard, warehouse=self.wh_a), Decimal("45.00"))

    def test_5_atomic_rollback_on_single_failing_item(self):
        # Laptop = 100 available, Keyboard = 2 available
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))
        StockService.receive(self.keyboard, warehouse=self.wh_a, quantity=Decimal("2.00"))

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
        # 10 Laptops (Sufficient), 5 Keyboards (Insufficient)
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)
        InvoiceItem.objects.create(invoice=inv, product=self.keyboard, qty=Decimal("5.00"), unit_price=self.keyboard.selling_price)

        with self.assertRaises(InsufficientStockError):
            InvoiceService.complete_invoice(inv)

        # Zero partial deduction: Laptop remains 100, Keyboard remains 2
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.keyboard, warehouse=self.wh_a), Decimal("2.00"))

    def test_6_duplicate_completion_protection(self):
        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("100.00"))

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

        # First completion
        InvoiceService.complete_invoice(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

        # Second completion call
        InvoiceService.complete_invoice(inv)
        # Stock remains 90 (deducted only ONCE)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

    def test_7_invoice_cancellation_restores_stock(self):
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

        # Sale completed: Stock = 90
        InvoiceService.complete_invoice(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

        # Cancel Invoice: Stock restored to 100
        InvoiceService.cancel_invoice(inv)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))
        self.assertEqual(inv.status, "CANCELLED")

        # Verify audit movements preserved (both OUT and IN recorded)
        movements = StockMovement.objects.filter(reference_id=inv.id)
        self.assertEqual(movements.count(), 2)

    def test_8_api_invoice_complete_and_insufficient_stock(self):
        self.client.force_authenticate(user=self.user_a)

        StockService.receive(self.laptop, warehouse=self.wh_a, quantity=Decimal("5.00"))

        today = timezone.now().date()
        inv = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-TEST-008",
            customer=self.customer_a,
            warehouse=self.wh_a,
            invoice_date=today,
            due_date=today,
            status="DRAFT"
        )
        InvoiceItem.objects.create(invoice=inv, product=self.laptop, qty=Decimal("10.00"), unit_price=self.laptop.selling_price)

        # POST /api/v1/invoices/<id>/complete/
        response = self.client.post(f"/api/v1/invoices/{inv.id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "insufficient_stock")
