from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.exceptions import (
    BusinessRuleError,
    InsufficientStockError,
    InvalidDocumentStatusError,
)

from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
    MOVEMENT_TYPE_PURCHASE_RETURN,
)

from inventory.models import (
    Warehouse,
    StockMovement,
    PurchaseReturnDocument,
    PurchaseReturnDocumentItem,
    InventoryItem,
)

from inventory.services import StockService
from inventory.purchase_return_services import PurchaseReturnService

from invoices.models import Organization, Product, Role, Permission, OrganizationMembership
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem

User = get_user_model()


class PurchaseReturnServiceTestCase(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(name="Return Test Org", slug="return-test-org")
        self.warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Main Warehouse",
            code="WH-MAIN"
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Acme Hardware Ltd",
            email="supplier@acme.com"
        )

        self.user_creator = User.objects.create_user(username="creator", email="creator@test.com", password="pass")
        self.user_approver = User.objects.create_user(username="approver", email="approver@test.com", password="pass")

        self.role_member = Role.objects.create(name="Member Role", slug="member-role")
        self.role_approver = Role.objects.create(name="Approver Role", slug="approver-role")

        # Grant approval permission
        perm, _ = Permission.objects.get_or_create(code="purchase_return.approve", defaults={"name": "Approve Returns"})
        self.role_approver.permissions.add(perm)

        OrganizationMembership.objects.create(user=self.user_creator, organization=self.org, role=self.role_member)
        OrganizationMembership.objects.create(user=self.user_approver, organization=self.org, role=self.role_approver)

        self.product_a = Product.objects.create(
            organization=self.org,
            name="Router A",
            sku="RTR-A",
            is_stockable=True,
            selling_price=Decimal("150.00")
        )
        self.product_b = Product.objects.create(
            organization=self.org,
            name="Switch B",
            sku="SWT-B",
            is_stockable=True,
            selling_price=Decimal("250.00")
        )

        # Initial stock receiving
        StockService.receive(
            product=self.product_a,
            warehouse=self.warehouse,
            quantity=Decimal("50.00"),
            reference_type="INITIAL",
            reference_id=1,
            notes="Initial stock"
        )
        StockService.receive(
            product=self.product_b,
            warehouse=self.warehouse,
            quantity=Decimal("20.00"),
            reference_type="INITIAL",
            reference_id=2,
            notes="Initial stock"
        )

        # Purchase Order
        self.po = PurchaseOrder.objects.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            order_number="PO-2026-001",
            order_date=timezone.now().date(),
            status="APPROVED"
        )
        self.po_item_a = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            product=self.product_a,
            quantity=Decimal("20.00"),
            unit_cost=Decimal("100.00"),
            received_quantity=Decimal("20.00")  # Simulate 20 received
        )

    def test_01_create_return_draft(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-001",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator,
            notes="Defective routers"
        )
        item = PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("5.00"),
            reason="Faulty port"
        )
        self.assertEqual(pr.status, DOC_STATUS_DRAFT)
        self.assertEqual(pr.items.count(), 1)
        self.assertEqual(item.quantity, Decimal("5.00"))

    def test_02_submit_draft(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-002",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("5.00")
        )
        PurchaseReturnService.submit(pr)
        self.assertEqual(pr.status, DOC_STATUS_PENDING)

    def test_03_approval_and_self_approval_restriction(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-003",
            return_date=timezone.now().date(),
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("5.00")
        )
        PurchaseReturnService.submit(pr)

        # Creator approving self must fail
        with self.assertRaises(BusinessRuleError):
            PurchaseReturnService.approve(pr, approved_by=self.user_creator)

        # Approver approves
        PurchaseReturnService.approve(pr, approved_by=self.user_approver)
        self.assertEqual(pr.status, DOC_STATUS_APPROVED)
        self.assertEqual(pr.approved_by, self.user_approver)

    def test_04_completion_decreases_stock_and_creates_ledger_entry(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-004",
            return_date=timezone.now().date(),
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("5.00")
        )
        PurchaseReturnService.submit(pr)
        PurchaseReturnService.approve(pr, approved_by=self.user_approver)

        initial_bal = StockService.get_balance(self.product_a, self.warehouse)
        pr, movements = PurchaseReturnService.complete(pr, completed_by=self.user_approver)

        self.assertEqual(pr.status, DOC_STATUS_COMPLETED)
        new_bal = StockService.get_balance(self.product_a, self.warehouse)
        self.assertEqual(new_bal, initial_bal - Decimal("5.00"))

        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, MOVEMENT_TYPE_PURCHASE_RETURN)
        self.assertEqual(movements[0].quantity, Decimal("-5.00"))

    def test_05_cannot_return_more_than_received(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-005",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        # Received was 20.00, attempting to return 25.00
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("25.00")
        )
        with self.assertRaises(BusinessRuleError) as cm:
            PurchaseReturnService.submit(pr)
        self.assertIn("Returnable quantity is 20", str(cm.exception))

    def test_06_cannot_return_more_than_current_stock(self):
        # Set stock of Product B to 5.00
        inv = InventoryItem.objects.get(product=self.product_b, warehouse=self.warehouse)
        inv.quantity = Decimal("5.00")
        inv.save()

        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-006",
            return_date=timezone.now().date(),
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_b,
            quantity=Decimal("10.00")
        )
        PurchaseReturnService.submit(pr)

        with self.assertRaises(InsufficientStockError):
            PurchaseReturnService.approve(pr, approved_by=self.user_approver)

    def test_07_product_not_on_po_fails(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-007",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        # Product B is not on PO
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_b,
            quantity=Decimal("2.00")
        )
        with self.assertRaises(BusinessRuleError) as cm:
            PurchaseReturnService.submit(pr)
        self.assertIn("does not exist on the purchase order", str(cm.exception))

    def test_08_different_organization_validation_fails(self):
        other_org = Organization.objects.create(name="Other Org", slug="other-org")
        other_supplier = Supplier.objects.create(
            organization=other_org,
            company_name="Other Supplier"
        )
        with self.assertRaises(BusinessRuleError):
            PurchaseReturnService.create(
                organization=self.org,
                supplier=other_supplier,
                warehouse=self.warehouse,
                document_number="PR-008",
                return_date=timezone.now().date()
            )

    def test_09_partial_return_tracks_remaining(self):
        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-009",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(
            purchase_return=pr,
            product=self.product_a,
            quantity=Decimal("5.00")
        )
        PurchaseReturnService.submit(pr)
        PurchaseReturnService.approve(pr, approved_by=self.user_approver)
        PurchaseReturnService.complete(pr, completed_by=self.user_approver)

        returned_qty = PurchaseReturnService.get_returned_quantity(self.po, self.product_a)
        self.assertEqual(returned_qty, Decimal("5.00"))

    def test_10_multiple_returns_cumulative_cap(self):
        # First Return: 5
        pr1 = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-010-1",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(purchase_return=pr1, product=self.product_a, quantity=Decimal("5.00"))
        PurchaseReturnService.submit(pr1)
        PurchaseReturnService.approve(pr1, approved_by=self.user_approver)
        PurchaseReturnService.complete(pr1, completed_by=self.user_approver)

        # Second Return: 10
        pr2 = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-010-2",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(purchase_return=pr2, product=self.product_a, quantity=Decimal("10.00"))
        PurchaseReturnService.submit(pr2)
        PurchaseReturnService.approve(pr2, approved_by=self.user_approver)
        PurchaseReturnService.complete(pr2, completed_by=self.user_approver)

        # Third Return: 6 (Remaining returnable is 20 - 15 = 5)
        pr3 = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-010-3",
            return_date=timezone.now().date(),
            purchase_order=self.po,
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(purchase_return=pr3, product=self.product_a, quantity=Decimal("6.00"))
        with self.assertRaises(BusinessRuleError) as cm:
            PurchaseReturnService.submit(pr3)
        self.assertIn("Returnable quantity is 5", str(cm.exception))

    def test_11_atomic_multi_item_return(self):
        # Product A stock = 50, Product B stock set to 2
        inv_b = InventoryItem.objects.get(product=self.product_b, warehouse=self.warehouse)
        inv_b.quantity = Decimal("2.00")
        inv_b.save()

        pr = PurchaseReturnService.create(
            organization=self.org,
            supplier=self.supplier,
            warehouse=self.warehouse,
            document_number="PR-011",
            return_date=timezone.now().date(),
            created_by=self.user_creator
        )
        PurchaseReturnService.add_item(purchase_return=pr, product=self.product_a, quantity=Decimal("10.00"))
        PurchaseReturnService.add_item(purchase_return=pr, product=self.product_b, quantity=Decimal("5.00"))  # Exceeds B stock (2)

        PurchaseReturnService.submit(pr)

        with self.assertRaises(InsufficientStockError):
            PurchaseReturnService.approve(pr, approved_by=self.user_approver)

        # Check stock of Product A remained 50.00
        bal_a = StockService.get_balance(self.product_a, self.warehouse)
        self.assertEqual(bal_a, Decimal("50.00"))
