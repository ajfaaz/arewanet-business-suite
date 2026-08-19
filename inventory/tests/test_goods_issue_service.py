from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from invoices.models import Organization, Product, ProductCategory
from inventory.models import (
    Warehouse, InventoryItem, StockMovement,
    GoodsIssueNote, GoodsIssueNoteItem,
)
from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_CANCELLED,
)
from inventory.document_services import GoodsIssueService
from inventory.services import StockService
from core.exceptions import BusinessRuleError, InsufficientStockError

User = get_user_model()


class GoodsIssueServiceTestCase(TestCase):

    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(name="ArewaNet Enterprise", slug="arewanet-gin-test")
        self.user_a = User.objects.create_user(username="gin_user_a", password="password123")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Hardware")
        self.prod_a1 = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Router",
            sku="RTR-01",
            selling_price=Decimal("50000.00")
        )
        self.prod_a2 = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Laptop",
            sku="LPT-01",
            selling_price=Decimal("350000.00")
        )

        self.wh_a1 = Warehouse.objects.create(organization=self.org_a, name="Main Warehouse Kano", code="WH-KNO-GIN")

        # Organization B
        self.org_b = Organization.objects.create(name="Sahara Telecoms", slug="sahara-gin-test")
        self.user_b = User.objects.create_user(username="gin_user_b", password="password123")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Sahara Warehouse", code="WH-SAH-GIN")
        self.prod_b = Product.objects.create(
            organization=self.org_b,
            name="Org B Fiber Cable",
            sku="FBR-01",
            selling_price=Decimal("15000.00")
        )

        self.today = timezone.now().date()

    def test_create_gin(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000001",
            issue_date=self.today,
            created_by=self.user_a,
            notes="Initial GIN test"
        )
        self.assertEqual(gin.status, DOC_STATUS_DRAFT)
        self.assertEqual(gin.organization, self.org_a)
        self.assertEqual(gin.warehouse, self.wh_a1)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_add_item(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000002",
            issue_date=self.today,
            created_by=self.user_a,
        )
        item = GoodsIssueService.add_item(
            gin=gin,
            product=self.prod_a1,
            quantity=Decimal("10.00")
        )
        self.assertEqual(item.gin, gin)
        self.assertEqual(item.product, self.prod_a1)
        self.assertEqual(item.quantity, Decimal("10.00"))
        self.assertEqual(gin.items.count(), 1)

    def test_submit(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000003",
            issue_date=self.today,
            created_by=self.user_a,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        
        submitted_gin = GoodsIssueService.submit(gin)
        self.assertEqual(submitted_gin.status, DOC_STATUS_PENDING)

    def test_approve(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000004",
            issue_date=self.today,
            created_by=self.user_a,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        GoodsIssueService.submit(gin)

        approved_gin = GoodsIssueService.approve(gin, approved_by=self.user_a)
        self.assertEqual(approved_gin.status, DOC_STATUS_APPROVED)
        self.assertEqual(approved_gin.approved_by, self.user_a)
        self.assertIsNotNone(approved_gin.approved_at)

    def test_complete(self):
        # 1. Stock setup: receive 50 units
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=1
        )
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("50.00"))

        # 2. GIN lifecycle: issue 20 units
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000005",
            issue_date=self.today,
            created_by=self.user_a,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("20.00"))
        GoodsIssueService.submit(gin)
        GoodsIssueService.approve(gin, approved_by=self.user_a)

        # 3. Complete GIN
        completed_gin, movements = GoodsIssueService.complete(gin, completed_by=self.user_a)
        
        self.assertEqual(completed_gin.status, DOC_STATUS_COMPLETED)
        self.assertEqual(completed_gin.completed_by, self.user_a)
        self.assertIsNotNone(completed_gin.completed_at)
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].quantity, Decimal("-20.00"))
        
        # Verify balance decreased to 30
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("30.00"))

    def test_insufficient_stock(self):
        # Stock = 10, GIN requests = 15
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("10.00"),
            reference_type="TEST",
            reference_id=2
        )

        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000006",
            issue_date=self.today,
            created_by=self.user_a,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("15.00"))
        GoodsIssueService.submit(gin)
        GoodsIssueService.approve(gin, approved_by=self.user_a)

        # Execution of complete should raise InsufficientStockError
        with self.assertRaises(InsufficientStockError):
            GoodsIssueService.complete(gin, completed_by=self.user_a)

        # Stock remains 10 and GIN status remains APPROVED
        gin.refresh_from_db()
        self.assertEqual(gin.status, DOC_STATUS_APPROVED)
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("10.00"))

    def test_multi_item_atomicity(self):
        # Stock: Router = 100, Laptop = 2
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("100.00"),
            reference_type="TEST",
            reference_id=3
        )
        StockService.receive(
            product=self.prod_a2,
            warehouse=self.wh_a1,
            quantity=Decimal("2.00"),
            reference_type="TEST",
            reference_id=4
        )

        # GIN requests: Router = 20, Laptop = 10 (Laptop will fail)
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000007",
            issue_date=self.today,
            created_by=self.user_a,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("20.00"))
        GoodsIssueService.add_item(gin=gin, product=self.prod_a2, quantity=Decimal("10.00"))
        GoodsIssueService.submit(gin)
        GoodsIssueService.approve(gin, approved_by=self.user_a)

        initial_movement_count = StockMovement.objects.count()

        with self.assertRaises(InsufficientStockError):
            GoodsIssueService.complete(gin, completed_by=self.user_a)

        # Assert full rollback: Router remains 100, Laptop remains 2, no GIN movements created
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.prod_a2, self.wh_a1), Decimal("2.00"))
        self.assertEqual(StockMovement.objects.count(), initial_movement_count)
        
        gin.refresh_from_db()
        self.assertEqual(gin.status, DOC_STATUS_APPROVED)

    def test_organization_isolation(self):
        # Warehouse mismatch when creating GIN
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.create(
                organization=self.org_a,
                warehouse=self.wh_b,
                document_number="GIN-2026-INVALID",
                issue_date=self.today,
            )

        # Product mismatch when adding item
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000008",
            issue_date=self.today,
        )
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.add_item(gin=gin, product=self.prod_b, quantity=Decimal("5.00"))

    def test_status_protection(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000009",
            issue_date=self.today,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))

        # DRAFT -> cannot approve directly
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.approve(gin, approved_by=self.user_a)

        # PENDING -> cannot complete directly
        GoodsIssueService.submit(gin)
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.complete(gin, completed_by=self.user_a)

        # APPROVED -> cannot submit again
        GoodsIssueService.approve(gin, approved_by=self.user_a)
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.submit(gin)

        # Stock setup for completion
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("10.00"),
            reference_type="TEST",
            reference_id=5
        )
        GoodsIssueService.complete(gin, completed_by=self.user_a)

        # COMPLETED -> cannot cancel
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.cancel(gin)
