from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Invoice, InvoiceItem, Product, ProductCategory
from inventory.models import (
    Warehouse, InventoryItem, StockMovement,
    GoodsIssueNote, GoodsIssueNoteItem,
)
from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
)
from inventory.document_services import GoodsIssueService
from inventory.services import StockService
from core.exceptions import BusinessRuleError, InsufficientStockError, WarehouseOrganizationMismatch

User = get_user_model()


class GoodsIssueInvoiceIntegrationTestCase(TestCase):

    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(name="ArewaNet Systems", slug="arewanet-gin-inv-test")
        self.user_a = User.objects.create_superuser(username="gin_inv_creator", email="creator@test.com", password="password123")
        self.approver_a = User.objects.create_superuser(username="gin_inv_approver", email="approver@test.com", password="password123")

        self.customer_a = Customer.objects.create(organization=self.org_a, company_name="Kano Tech Ltd", email="kano@tech.ng", phone="08012345678", address="Kano")
        self.wh_a = Warehouse.objects.create(organization=self.org_a, name="Central Warehouse", code="WH-CNT-01")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Hardware")
        
        # Stockable Products
        self.prod_router = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Cisco Router",
            sku="RTR-2901",
            selling_price=Decimal("150000.00"),
            is_stockable=True,
        )
        self.prod_switch = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Cisco Switch",
            sku="SWT-2960",
            selling_price=Decimal("80000.00"),
            is_stockable=True,
        )

        # Non-stockable Product / Service
        self.prod_service = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Installation & Setup Service",
            sku="SRV-INST",
            selling_price=Decimal("25000.00"),
            is_stockable=False,
        )

        # Organization B (for cross-tenant tests)
        self.org_b = Organization.objects.create(name="Sahara Networks", slug="sahara-gin-inv-test")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Sahara WH", code="WH-SAH-01")

        self.today = timezone.now().date()

        # Base Invoice #1 (Router x 10, Switch x 5, Service x 1)
        self.invoice1 = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-2026-00010",
            customer=self.customer_a,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal("1925000.00"),
            total_due=Decimal("1925000.00"),
            status="UNPAID",
        )
        self.inv_item_router = InvoiceItem.objects.create(
            invoice=self.invoice1,
            product=self.prod_router,
            description="Router unit",
            qty=Decimal("10.00"),
            unit_price=Decimal("150000.00"),
        )
        self.inv_item_switch = InvoiceItem.objects.create(
            invoice=self.invoice1,
            product=self.prod_switch,
            description="Switch unit",
            qty=Decimal("5.00"),
            unit_price=Decimal("80000.00"),
        )
        self.inv_item_service = InvoiceItem.objects.create(
            invoice=self.invoice1,
            product=self.prod_service,
            description="Installation fee",
            qty=Decimal("1.00"),
            unit_price=Decimal("25000.00"),
        )

        # API Client setup
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_a)

    def test_1_create_gin_linked_to_invoice(self):
        gin = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[
                {"product": self.prod_router, "quantity": Decimal("4.00")},
                {"product": self.prod_switch, "quantity": Decimal("2.00")},
            ],
            document_number="GIN-INV-001"
        )
        self.assertEqual(gin.invoice, self.invoice1)
        self.assertEqual(gin.status, DOC_STATUS_DRAFT)
        self.assertEqual(gin.items.count(), 2)

    def test_2_cross_organization_warehouse_rejected(self):
        with self.assertRaises(WarehouseOrganizationMismatch):
            GoodsIssueService.create_from_invoice(
                invoice=self.invoice1,
                warehouse=self.wh_b,
                created_by=self.user_a,
                items=[{"product": self.prod_router, "quantity": Decimal("1.00")}],
                document_number="GIN-INV-CROSS-ORG"
            )

    def test_3_product_not_on_invoice_rejected(self):
        prod_other = Product.objects.create(
            organization=self.org_a,
            name="Uninvoiced Modem",
            sku="MDM-01",
            selling_price=Decimal("10000.00"),
            is_stockable=True,
        )
        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.create_from_invoice(
                invoice=self.invoice1,
                warehouse=self.wh_a,
                created_by=self.user_a,
                items=[{"product": prod_other, "quantity": Decimal("1.00")}],
                document_number="GIN-INV-UNINVOICED-PROD"
            )
        self.assertIn("does not exist on the invoice", str(ctx.exception))

    def test_4_over_fulfillment_rejected(self):
        # Invoice has Router x 10. Attempting GIN for 12 must be rejected.
        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.create_from_invoice(
                invoice=self.invoice1,
                warehouse=self.wh_a,
                created_by=self.user_a,
                items=[{"product": self.prod_router, "quantity": Decimal("12.00")}],
                document_number="GIN-INV-OVER-FULFILL"
            )
        self.assertIn("Invoice remaining quantity is 10.00", str(ctx.exception))

    def test_5_partial_fulfillment_calculation(self):
        # Initial status before any completion
        self.assertEqual(self.invoice1.fulfillment_status, "UNFULFILLED")

        # Receive stock
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=100
        )

        # Issue 4 out of 10 routers on GIN #1
        gin1 = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[{"product": self.prod_router, "quantity": Decimal("4.00")}],
            document_number="GIN-INV-PARTIAL-1"
        )
        GoodsIssueService.submit(gin1)
        GoodsIssueService.approve(gin1, approved_by=self.approver_a)
        GoodsIssueService.complete(gin1, completed_by=self.approver_a)

        fulfillment = GoodsIssueService.get_invoice_fulfillment(self.invoice1)
        router_data = fulfillment[self.prod_router.id]
        self.assertEqual(router_data["invoiced"], Decimal("10.00"))
        self.assertEqual(router_data["issued"], Decimal("4.00"))
        self.assertEqual(router_data["remaining"], Decimal("6.00"))

        self.assertEqual(self.invoice1.fulfillment_status, "PARTIALLY_FULFILLED")

    def test_6_full_fulfillment_status(self):
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=101
        )
        StockService.receive(
            product=self.prod_switch,
            warehouse=self.wh_a,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=102
        )

        # GIN #1: 4 routers, 5 switches
        gin1 = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[
                {"product": self.prod_router, "quantity": Decimal("4.00")},
                {"product": self.prod_switch, "quantity": Decimal("5.00")},
            ],
            document_number="GIN-INV-FULL-1"
        )
        GoodsIssueService.submit(gin1)
        GoodsIssueService.approve(gin1, approved_by=self.approver_a)
        GoodsIssueService.complete(gin1, completed_by=self.approver_a)

        # GIN #2: remaining 6 routers
        gin2 = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[{"product": self.prod_router, "quantity": Decimal("6.00")}],
            document_number="GIN-INV-FULL-2"
        )
        GoodsIssueService.submit(gin2)
        GoodsIssueService.approve(gin2, approved_by=self.approver_a)
        GoodsIssueService.complete(gin2, completed_by=self.approver_a)

        fulfillment = GoodsIssueService.get_invoice_fulfillment(self.invoice1)
        self.assertEqual(fulfillment[self.prod_router.id]["remaining"], Decimal("0.00"))
        self.assertEqual(fulfillment[self.prod_switch.id]["remaining"], Decimal("0.00"))

        self.assertEqual(self.invoice1.fulfillment_status, "FULFILLED")

    def test_7_non_stockable_product_rejected(self):
        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.create_from_invoice(
                invoice=self.invoice1,
                warehouse=self.wh_a,
                created_by=self.user_a,
                items=[{"product": self.prod_service, "quantity": Decimal("1.00")}],
                document_number="GIN-INV-SERVICE-FAIL"
            )
        self.assertIn("is not stockable and cannot be issued", str(ctx.exception))

    def test_8_invoice_creation_does_not_deduct_inventory(self):
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=103
        )
        initial_balance = StockService.get_balance(self.prod_router, self.wh_a)
        initial_movement_count = StockMovement.objects.count()

        # Creating Invoice #2
        inv2 = Invoice.objects.create(
            organization=self.org_a,
            invoice_no="INV-2026-00020",
            customer=self.customer_a,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal("1500000.00"),
            total_due=Decimal("1500000.00"),
            status="UNPAID",
        )
        InvoiceItem.objects.create(
            invoice=inv2,
            product=self.prod_router,
            qty=Decimal("10.00"),
            unit_price=Decimal("150000.00"),
        )

        # Inventory balance and movements must remain untouched
        self.assertEqual(StockService.get_balance(self.prod_router, self.wh_a), initial_balance)
        self.assertEqual(StockMovement.objects.count(), initial_movement_count)

    def test_9_gin_completion_deducts_inventory(self):
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=104
        )
        self.assertEqual(StockService.get_balance(self.prod_router, self.wh_a), Decimal("50.00"))

        gin = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[{"product": self.prod_router, "quantity": Decimal("10.00")}],
            document_number="GIN-INV-DEDUCT"
        )
        GoodsIssueService.submit(gin)
        GoodsIssueService.approve(gin, approved_by=self.approver_a)
        GoodsIssueService.complete(gin, completed_by=self.approver_a)

        # Balance reduced from 50 to 40, StockMovement created with -10
        self.assertEqual(StockService.get_balance(self.prod_router, self.wh_a), Decimal("40.00"))
        movement = StockMovement.objects.filter(reference_type="GIN", reference_id=gin.id).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal("-10.00"))

    def test_10_atomic_multi_item_failure_rollback(self):
        # Stock: Router = 100, Switch = 2
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("100.00"),
            reference_type="TEST",
            reference_id=105
        )
        StockService.receive(
            product=self.prod_switch,
            warehouse=self.wh_a,
            quantity=Decimal("2.00"),
            reference_type="TEST",
            reference_id=106
        )

        gin = GoodsIssueService.create_from_invoice(
            invoice=self.invoice1,
            warehouse=self.wh_a,
            created_by=self.user_a,
            items=[
                {"product": self.prod_router, "quantity": Decimal("5.00")},
                {"product": self.prod_switch, "quantity": Decimal("5.00")}, # Only 2 available!
            ],
            document_number="GIN-INV-ATOMIC-FAIL"
        )
        GoodsIssueService.submit(gin)

        # Approval fails pre-check due to Switch shortage
        with self.assertRaises(InsufficientStockError):
            GoodsIssueService.approve(gin, approved_by=self.approver_a)

        # Routers remain 100, Switches remain 2, no GIN movements created
        self.assertEqual(StockService.get_balance(self.prod_router, self.wh_a), Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.prod_switch, self.wh_a), Decimal("2.00"))
        self.assertEqual(StockMovement.objects.filter(reference_type="GIN", reference_id=gin.id).count(), 0)

    def test_11_api_endpoints_workflow(self):

        # 1. API POST create GIN from Invoice
        response = self.client.post(
            f"/api/invoices/{self.invoice1.id}/goods-issues/",
            {
                "warehouse_id": self.wh_a.id,
                "items": [
                    {"product_id": self.prod_router.id, "quantity": "3.00"}
                ]
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        gin_id = response.data["id"]
        self.assertEqual(response.data["status"], DOC_STATUS_DRAFT)

        # 2. API POST submit
        response = self.client.post(f"/api/goods-issues/{gin_id}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], DOC_STATUS_PENDING)

        # Stock setup for approval
        StockService.receive(
            product=self.prod_router,
            warehouse=self.wh_a,
            quantity=Decimal("20.00"),
            reference_type="TEST",
            reference_id=107
        )

        # 3. API POST approve (approver user)
        self.client.force_authenticate(user=self.approver_a)
        response = self.client.post(f"/api/goods-issues/{gin_id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], DOC_STATUS_APPROVED)

        # 4. API POST complete
        response = self.client.post(f"/api/goods-issues/{gin_id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], DOC_STATUS_COMPLETED)
        self.assertEqual(response.data["movement_count"], 1)

        self.assertEqual(StockService.get_balance(self.prod_router, self.wh_a), Decimal("17.00"))
