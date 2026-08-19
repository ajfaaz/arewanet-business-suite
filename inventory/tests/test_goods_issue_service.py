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
        
        # Superuser creator & approver for authorization test cases
        self.creator_user = User.objects.create_superuser(username="gin_creator", email="creator@test.com", password="password123")
        self.approver_user = User.objects.create_superuser(username="gin_approver", email="approver@test.com", password="password123")
        self.unauthorized_user = User.objects.create_user(username="gin_unauth", password="password123")

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
        self.user_b = User.objects.create_superuser(username="gin_user_b", email="userb@test.com", password="password123")
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
            created_by=self.creator_user,
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
            created_by=self.creator_user,
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

    def test_submit_validation_success(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000003",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        
        submitted_gin = GoodsIssueService.submit(gin)
        self.assertEqual(submitted_gin.status, DOC_STATUS_PENDING)

    def test_submit_validation_empty_items(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-EMPTY",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.submit(gin)
        self.assertIn("at least one item", str(ctx.exception))

    def test_submit_validation_duplicate_products(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-DUP",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueNoteItem.objects.create(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        GoodsIssueNoteItem.objects.create(gin=gin, product=self.prod_a1, quantity=Decimal("10.00"))

        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.submit(gin)
        self.assertIn("appears more than once", str(ctx.exception))

    def test_approval_stock_precheck_failure(self):
        # Stock = 10, GIN = 15
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("10.00"),
            reference_type="TEST",
            reference_id=1
        )

        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-SHORTAGE",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("15.00"))
        GoodsIssueService.submit(gin)

        # Attempt approval when stock is insufficient
        with self.assertRaises(InsufficientStockError) as ctx:
            GoodsIssueService.approve(gin, approved_by=self.approver_user)
        
        self.assertIn("Router", str(ctx.exception))
        self.assertIn("required=15.00", str(ctx.exception))
        self.assertIn("available=10.00", str(ctx.exception))
        self.assertIn("shortage=5.00", str(ctx.exception))

        gin.refresh_from_db()
        self.assertEqual(gin.status, DOC_STATUS_PENDING)

    def test_approval_success_and_self_approval_protection(self):
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("20.00"),
            reference_type="TEST",
            reference_id=2
        )

        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000004",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        GoodsIssueService.submit(gin)

        # Self-approval by creator must be rejected
        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.approve(gin, approved_by=self.creator_user)
        self.assertIn("cannot approve it", str(ctx.exception))

        # Approval by distinct authorized approver succeeds
        approved_gin = GoodsIssueService.approve(gin, approved_by=self.approver_user)
        self.assertEqual(approved_gin.status, DOC_STATUS_APPROVED)
        self.assertEqual(approved_gin.approved_by, self.approver_user)
        self.assertIsNotNone(approved_gin.approved_at)

    def test_permission_enforcement(self):
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-PERM",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))
        GoodsIssueService.submit(gin)

        # Approval attempt by unauthenticated or unauthorized user raises error
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.approve(gin, approved_by=None)

        with self.assertRaises(BusinessRuleError) as ctx:
            GoodsIssueService.approve(gin, approved_by=self.unauthorized_user)
        self.assertIn("User does not have permission", str(ctx.exception))

    def test_complete_success(self):
        # 1. Stock setup: receive 50 units
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("50.00"),
            reference_type="TEST",
            reference_id=3
        )

        # 2. GIN lifecycle
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-000005",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("20.00"))
        GoodsIssueService.submit(gin)
        GoodsIssueService.approve(gin, approved_by=self.approver_user)

        # 3. Complete GIN
        completed_gin, movements = GoodsIssueService.complete(gin, completed_by=self.approver_user)
        
        self.assertEqual(completed_gin.status, DOC_STATUS_COMPLETED)
        self.assertEqual(completed_gin.completed_by, self.approver_user)
        self.assertIsNotNone(completed_gin.completed_at)
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].quantity, Decimal("-20.00"))
        
        # Verify balance decreased to 30
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("30.00"))

    def test_multi_item_completion_is_atomic(self):
        # Initial Stock: Router = 100, Laptop = 15
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("100.00"),
            reference_type="TEST",
            reference_id=4
        )
        StockService.receive(
            product=self.prod_a2,
            warehouse=self.wh_a1,
            quantity=Decimal("15.00"),
            reference_type="TEST",
            reference_id=5
        )

        # GIN requests: Router = 20, Laptop = 10
        gin = GoodsIssueService.create(
            organization=self.org_a,
            warehouse=self.wh_a1,
            document_number="GIN-2026-ATOMIC",
            issue_date=self.today,
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("20.00"))
        GoodsIssueService.add_item(gin=gin, product=self.prod_a2, quantity=Decimal("10.00"))
        GoodsIssueService.submit(gin)

        # Approval pre-check passes (Router=100 >= 20, Laptop=15 >= 10)
        GoodsIssueService.approve(gin, approved_by=self.approver_user)
        self.assertEqual(gin.status, DOC_STATUS_APPROVED)

        # Simulate another concurrent transaction depleting Laptop stock to 2 between approval and completion
        StockService.issue(
            product=self.prod_a2,
            warehouse=self.wh_a1,
            quantity=Decimal("13.00"),
            movement_type="SALE",
            reference_type="TEST_OTHER",
            reference_id=99
        )
        self.assertEqual(StockService.get_balance(self.prod_a2, self.wh_a1), Decimal("2.00"))

        initial_gin_movement_count = StockMovement.objects.filter(reference_type="GIN", reference_id=gin.id).count()

        # Completion attempt must perform locked stock check and fail atomically
        with self.assertRaises(InsufficientStockError) as ctx:
            GoodsIssueService.complete(gin, completed_by=self.approver_user)
        
        self.assertIn("Laptop", str(ctx.exception))
        self.assertIn("required=10.00", str(ctx.exception))
        self.assertIn("available=2.00", str(ctx.exception))

        # Assert full rollback: Router balance remains 100, Laptop balance remains 2
        self.assertEqual(StockService.get_balance(self.prod_a1, self.wh_a1), Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.prod_a2, self.wh_a1), Decimal("2.00"))
        self.assertEqual(StockMovement.objects.filter(reference_type="GIN", reference_id=gin.id).count(), initial_gin_movement_count)
        
        gin.refresh_from_db()
        self.assertEqual(gin.status, DOC_STATUS_APPROVED)

    def test_organization_isolation(self):
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.create(
                organization=self.org_a,
                warehouse=self.wh_b,
                document_number="GIN-2026-INVALID",
                issue_date=self.today,
            )

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
            created_by=self.creator_user,
        )
        GoodsIssueService.add_item(gin=gin, product=self.prod_a1, quantity=Decimal("5.00"))

        # DRAFT -> cannot approve directly
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.approve(gin, approved_by=self.approver_user)

        # PENDING -> cannot complete directly
        GoodsIssueService.submit(gin)
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.complete(gin, completed_by=self.approver_user)

        # Stock setup for approval & completion
        StockService.receive(
            product=self.prod_a1,
            warehouse=self.wh_a1,
            quantity=Decimal("10.00"),
            reference_type="TEST",
            reference_id=6
        )

        # APPROVED -> cannot submit again
        GoodsIssueService.approve(gin, approved_by=self.approver_user)
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.submit(gin)

        GoodsIssueService.complete(gin, completed_by=self.approver_user)

        # COMPLETED -> cannot cancel
        with self.assertRaises(BusinessRuleError):
            GoodsIssueService.cancel(gin)
