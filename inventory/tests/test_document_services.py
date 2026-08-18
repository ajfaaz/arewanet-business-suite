from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from invoices.models import Organization, Product, ProductCategory
from inventory.models import (
    Warehouse, WarehouseLocation, InventoryItem, StockMovement,
    GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
)
from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_CANCELLED,
)
from inventory.document_services import InventoryDocumentService
from inventory.services import StockService
from core.exceptions import InvalidDocumentStatusError, WarehouseOrganizationMismatch, BusinessRuleError
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem

User = get_user_model()


class InventoryDocumentServicesTestCase(TestCase):

    def setUp(self):
        # Organization A Setup
        self.org_a = Organization.objects.create(name="ArewaNet Enterprise", slug="arewanet-enterprise")
        self.user_a = User.objects.create_user(username="docusera", password="password123")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Hardware")
        self.prod_a1 = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Server Rack 42U",
            sku="SRV-42U",
            selling_price=Decimal("450000.00")
        )
        self.prod_a2 = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Cat6 Patch Cable",
            sku="CBL-CAT6",
            selling_price=Decimal("2500.00")
        )

        self.wh_a1 = Warehouse.objects.create(organization=self.org_a, name="Central Warehouse Kano", code="WH-KNO")
        self.wh_a2 = Warehouse.objects.create(organization=self.org_a, name="Branch Warehouse Kaduna", code="WH-KDA")

        # Organization B Setup
        self.org_b = Organization.objects.create(name="Sahara Telecoms", slug="sahara-telecoms-doc")
        self.user_b = User.objects.create_user(username="docuserb", password="password123")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Sahara Warehouse", code="WH-SAHARA")

    def test_grn_full_lifecycle_and_stock_update(self):
        # 1. Create GRN (DRAFT)
        today = timezone.now().date()
        items_data = [
            {"product": self.prod_a1, "quantity": "50.00", "unit_cost": "350000.00"},
            {"product": self.prod_a2, "quantity": "200.00", "unit_cost": "1800.00"},
        ]
        grn = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=items_data,
            supplier_name="TechSupplies Ltd",
            notes="Bulk hardware stock arrival",
            user=self.user_a
        )

        self.assertEqual(grn.status, DOC_STATUS_DRAFT)
        self.assertTrue(grn.document_number.startswith("GRN-"))

        # Verify stock is UNCHANGED while in DRAFT
        bal_before = StockService.get_balance(self.prod_a1, warehouse=self.wh_a1)
        self.assertEqual(bal_before, Decimal("0.00"))

        # 2. Submit & Approve GRN
        InventoryDocumentService.submit_grn(grn)
        self.assertEqual(grn.status, DOC_STATUS_PENDING)

        InventoryDocumentService.approve_grn(grn, user=self.user_a)
        self.assertEqual(grn.status, DOC_STATUS_APPROVED)
        self.assertEqual(grn.approved_by, self.user_a)

        # 3. Complete GRN
        InventoryDocumentService.complete_grn(grn, user=self.user_a)
        self.assertEqual(grn.status, DOC_STATUS_COMPLETED)
        self.assertEqual(grn.completed_by, self.user_a)

        # Verify Stock Item & Ledger Movement created
        bal_after1 = StockService.get_balance(self.prod_a1, warehouse=self.wh_a1)
        bal_after2 = StockService.get_balance(self.prod_a2, warehouse=self.wh_a1)
        self.assertEqual(bal_after1, Decimal("50.00"))
        self.assertEqual(bal_after2, Decimal("200.00"))

        movements = StockMovement.objects.filter(reference_type="GRN", reference_id=grn.id)
        self.assertEqual(movements.count(), 2)

    def test_double_completion_protection(self):
        today = timezone.now().date()
        grn = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "10.00", "unit_cost": "100.00"}],
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn, user=self.user_a)
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("10.00"))

        # Second completion attempt must raise InvalidDocumentStatusError
        with self.assertRaises(InvalidDocumentStatusError):
            InventoryDocumentService.complete_grn(grn, user=self.user_a)

        # Balance must remain 10.00 (NO duplicate stock additions)
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("10.00"))
        self.assertEqual(StockMovement.objects.filter(reference_type="GRN", reference_id=grn.id).count(), 1)

    def test_cancelled_document_completion_protection(self):
        today = timezone.now().date()
        grn = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "10.00"}],
            user=self.user_a
        )
        InventoryDocumentService.cancel_grn(grn)
        self.assertEqual(grn.status, DOC_STATUS_CANCELLED)

        # Attempt to complete cancelled GRN must fail
        with self.assertRaises(InvalidDocumentStatusError):
            InventoryDocumentService.complete_grn(grn, user=self.user_a)

        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("0.00"))

    def test_gin_full_lifecycle_and_stock_issue(self):
        today = timezone.now().date()
        # Seed initial stock of 100 via StockService
        StockService.receive(self.prod_a1, warehouse=self.wh_a1, quantity=Decimal("100.00"))

        # Create GIN for 30 units
        gin = InventoryDocumentService.create_gin(
            organization=self.org_a,
            warehouse=self.wh_a1,
            issue_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "30.00"}],
            notes="Issuing equipment for client setup",
            user=self.user_a
        )

        InventoryDocumentService.approve_gin(gin, user=self.user_a)
        InventoryDocumentService.complete_gin(gin, user=self.user_a)

        self.assertEqual(gin.status, DOC_STATUS_COMPLETED)
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("70.00"))

    def test_stock_transfer_document_workflow(self):
        today = timezone.now().date()
        # Seed 100 in Kano Warehouse
        StockService.receive(self.prod_a1, warehouse=self.wh_a1, quantity=Decimal("100.00"))

        transfer_doc = InventoryDocumentService.create_transfer(
            organization=self.org_a,
            source_warehouse=self.wh_a1,
            destination_warehouse=self.wh_a2,
            transfer_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "25.00"}],
            notes="Inter-branch stock transfer",
            user=self.user_a
        )

        InventoryDocumentService.approve_transfer(transfer_doc, user=self.user_a)
        InventoryDocumentService.complete_transfer(transfer_doc, user=self.user_a)

        self.assertEqual(transfer_doc.status, DOC_STATUS_COMPLETED)
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("75.00"))
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a2), Decimal("25.00"))

    def test_stock_adjustment_document_workflow(self):
        today = timezone.now().date()
        # Initial system stock: 100
        StockService.receive(self.prod_a1, warehouse=self.wh_a1, quantity=Decimal("100.00"))

        # Physical count reveals 96 units
        adj = InventoryDocumentService.create_adjustment(
            organization=self.org_a,
            warehouse=self.wh_a1,
            adjustment_date=today,
            items_data=[{"product": self.prod_a1, "counted_quantity": "96.00", "reason": "Damaged unit write-off"}],
            notes="Quarterly audit reconciliation",
            user=self.user_a
        )

        self.assertEqual(adj.items.first().difference, Decimal("-4.00"))

        InventoryDocumentService.approve_adjustment(adj, user=self.user_a)
        InventoryDocumentService.complete_adjustment(adj, user=self.user_a)

        self.assertEqual(adj.status, DOC_STATUS_COMPLETED)
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("96.00"))

    def test_tenant_isolation_on_documents(self):
        today = timezone.now().date()
        with self.assertRaises(WarehouseOrganizationMismatch):
            InventoryDocumentService.create_grn(
                organization=self.org_a,
                warehouse=self.wh_b, # Belongs to Org B
                received_date=today,
                items_data=[{"product": self.prod_a1, "quantity": "10.00"}],
                user=self.user_a
            )

    def test_grn_po_receiving_partial_and_full(self):
        today = timezone.now().date()
        supplier = Supplier.objects.create(
            organization=self.org_a,
            company_name="Global Tech Supplies",
            email="sales@globaltech.com"
        )
        po = PurchaseOrder.objects.create(
            organization=self.org_a,
            supplier=supplier,
            warehouse=self.wh_a1,
            order_number="PO-2026-0001",
            order_date=today,
            status="APPROVED",
            created_by=self.user_a
        )
        po_item1 = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=self.prod_a1,
            quantity=Decimal("100.00"),
            unit_cost=Decimal("350000.00"),
            total_cost=Decimal("35000000.00")
        )

        # Partial receipt: receive 40 units out of 100
        grn1 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "40.00", "unit_cost": "350000.00"}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.approve_grn(grn1, user=self.user_a)
        InventoryDocumentService.complete_grn(grn1, user=self.user_a)

        po.refresh_from_db()
        po_item1.refresh_from_db()
        self.assertEqual(po.status, "PARTIAL_RECEIPT")
        self.assertEqual(po_item1.received_quantity, Decimal("40.00"))
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("40.00"))

        # Second receipt: receive remaining 60 units
        grn2 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "60.00", "unit_cost": "350000.00"}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.approve_grn(grn2, user=self.user_a)
        InventoryDocumentService.complete_grn(grn2, user=self.user_a)

        po.refresh_from_db()
        po_item1.refresh_from_db()
        self.assertEqual(po.status, "RECEIVED")
        self.assertEqual(po_item1.received_quantity, Decimal("100.00"))
        self.assertEqual(StockService.get_balance(self.prod_a1, warehouse=self.wh_a1), Decimal("100.00"))

    def test_grn_po_receiving_over_receive_protection(self):
        today = timezone.now().date()
        supplier = Supplier.objects.create(
            organization=self.org_a,
            company_name="Global Tech Supplies",
            email="sales@globaltech.com"
        )
        po = PurchaseOrder.objects.create(
            organization=self.org_a,
            supplier=supplier,
            warehouse=self.wh_a1,
            order_number="PO-2026-0002",
            order_date=today,
            status="APPROVED",
            created_by=self.user_a
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=self.prod_a1,
            quantity=Decimal("10.00"),
            unit_cost=Decimal("350000.00"),
            total_cost=Decimal("3500000.00")
        )

        grn = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "15.00"}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.approve_grn(grn, user=self.user_a)

        # Completing GRN with 15 units when PO only ordered 10 must raise BusinessRuleError
        with self.assertRaises(BusinessRuleError):
            InventoryDocumentService.complete_grn(grn, user=self.user_a)

    def test_grn_po_receiving_unapproved_po_protection(self):
        today = timezone.now().date()
        supplier = Supplier.objects.create(
            organization=self.org_a,
            company_name="Global Tech Supplies",
            email="sales@globaltech.com"
        )
        po = PurchaseOrder.objects.create(
            organization=self.org_a,
            supplier=supplier,
            warehouse=self.wh_a1,
            order_number="PO-2026-0003",
            order_date=today,
            status="DRAFT", # Unapproved draft PO
            created_by=self.user_a
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=self.prod_a1,
            quantity=Decimal("10.00"),
            unit_cost=Decimal("350000.00"),
            total_cost=Decimal("3500000.00")
        )

        grn = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a1,
            received_date=today,
            items_data=[{"product": self.prod_a1, "quantity": "5.00"}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.approve_grn(grn, user=self.user_a)

        # Completing GRN for DRAFT PO must raise BusinessRuleError
        with self.assertRaises(BusinessRuleError):
            InventoryDocumentService.complete_grn(grn, user=self.user_a)
