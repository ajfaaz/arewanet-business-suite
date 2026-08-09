from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, UserProfile
from inventory.models import Warehouse, GoodsReceivedNote, GoodsReceivedNoteItem
from inventory.services import StockService
from inventory.document_services import InventoryDocumentService
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem
from purchases.services import SupplierService, PurchaseService
from purchases.selectors import SupplierSelector, PurchaseOrderSelector
from core.exceptions import BusinessRuleError

User = get_user_model()


class PurchaseSupplierFoundationTestCase(TestCase):

    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(name="ArewaNet Logistics Org A", slug="arewanet-logistics-a")
        self.user_a = User.objects.create_user(username="purchasinguser_a", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Hardware")
        self.laptop = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="ThinkPad T14",
            sku="TP-T14",
            selling_price=Decimal("450000.00"),
            is_stockable=True
        )
        self.wh_a = Warehouse.objects.create(organization=self.org_a, name="Main Warehouse Org A", code="WH-A")

        # Organization B
        self.org_b = Organization.objects.create(name="Sahara Supplies Org B", slug="sahara-supplies-b")
        self.user_b = User.objects.create_user(username="purchasinguser_b", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Main Warehouse Org B", code="WH-B")

        # Supplier for Org A
        self.supplier_a = SupplierService.create_supplier(
            organization=self.org_a,
            data={
                "company_name": "Lenovo Authorized Distributor Ltd",
                "contact_person": "Aliyu Ahmed",
                "email": "sales@lenovo.ng",
                "phone": "08020000000"
            }
        )

        self.client = APIClient()

    def test_supplier_creation_code_generation_and_updates(self):
        # Verify supplier code auto-generated: SUP-000001
        self.assertEqual(self.supplier_a.code, "SUP-000001")
        self.assertEqual(self.supplier_a.company_name, "Lenovo Authorized Distributor Ltd")

        # Update supplier
        updated_supplier = SupplierService.update_supplier(
            supplier=self.supplier_a,
            data={"contact_person": "Mustapha Aliyu"}
        )
        self.assertEqual(updated_supplier.contact_person, "Mustapha Aliyu")

    def test_supplier_search_and_organization_isolation(self):
        # Create Supplier for Org B
        supplier_b = SupplierService.create_supplier(
            organization=self.org_b,
            data={"company_name": "Dell Global Partner"}
        )
        self.assertEqual(supplier_b.code, "SUP-000001") # SUP-000001 is scoped per organization!

        # List Org A suppliers
        suppliers_a = SupplierSelector.list(self.org_a)
        self.assertEqual(suppliers_a.count(), 1)
        self.assertNotIn(supplier_b, suppliers_a)

    def test_purchase_order_creation_totals_and_lifecycle(self):
        po = PurchaseService.create_purchase_order(
            organization=self.org_a,
            supplier=self.supplier_a,
            warehouse=self.wh_a,
            items_data=[
                {"product": self.laptop, "quantity": Decimal("10.00"), "unit_cost": Decimal("400000.00")}
            ],
            order_date=timezone.now().date(),
            notes="Initial batch of 10 ThinkPads",
            user=self.user_a
        )

        # Expected status: DRAFT
        self.assertEqual(po.status, "DRAFT")
        self.assertTrue(po.order_number.startswith("PO-"))
        # Totals calculated: 10 * 400,000 = 4,000,000.00
        self.assertEqual(po.subtotal, Decimal("4000000.00"))
        self.assertEqual(po.total, Decimal("4000000.00"))

        # Purchase Order creation MUST NOT affect stock
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("0.00"))

        # Transition: Submit -> Approve
        PurchaseService.submit_purchase_order(po)
        self.assertEqual(po.status, "SUBMITTED")

        PurchaseService.approve_purchase_order(po)
        self.assertEqual(po.status, "APPROVED")

    def test_purchase_order_cancel(self):
        po = PurchaseService.create_purchase_order(
            organization=self.org_a,
            supplier=self.supplier_a,
            warehouse=self.wh_a,
            items_data=[{"product": self.laptop, "quantity": Decimal("5.00"), "unit_cost": Decimal("400000.00")}],
            user=self.user_a
        )
        PurchaseService.cancel_purchase_order(po)
        self.assertEqual(po.status, "CANCELLED")

        # Attempting to submit or approve cancelled PO fails
        with self.assertRaises(BusinessRuleError):
            PurchaseService.submit_purchase_order(po)

    def test_partial_receiving_via_grn(self):
        # Create and Approve PO for 100 Laptops
        po = PurchaseService.create_purchase_order(
            organization=self.org_a,
            supplier=self.supplier_a,
            warehouse=self.wh_a,
            items_data=[{"product": self.laptop, "quantity": Decimal("100.00"), "unit_cost": Decimal("400000.00")}],
            user=self.user_a
        )
        PurchaseService.approve_purchase_order(po)

        # 1. Create and Complete GRN 1 for 40 Laptops
        grn1 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("40.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn1)

        # Check stock balance: +40
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("40.00"))

        # Check PO metrics
        po_item = po.items.get(product=self.laptop)
        self.assertEqual(po_item.received_quantity, Decimal("40.00"))
        self.assertEqual(po_item.remaining_quantity, Decimal("60.00"))
        self.assertEqual(po.status, "PARTIAL_RECEIPT")

        # 2. Create and Complete GRN 2 for 30 Laptops
        grn2 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("30.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn2)

        # Total stock = +70
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("70.00"))
        po_item.refresh_from_db()
        self.assertEqual(po_item.received_quantity, Decimal("70.00"))
        self.assertEqual(po_item.remaining_quantity, Decimal("30.00"))

    def test_over_receiving_protection(self):
        po = PurchaseService.create_purchase_order(
            organization=self.org_a,
            supplier=self.supplier_a,
            warehouse=self.wh_a,
            items_data=[{"product": self.laptop, "quantity": Decimal("100.00"), "unit_cost": Decimal("400000.00")}],
            user=self.user_a
        )
        PurchaseService.approve_purchase_order(po)

        # Receive 90
        grn1 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("90.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn1)

        # Attempt to receive 20 when only 10 remain
        grn_excess = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("20.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        with self.assertRaises(BusinessRuleError):
            InventoryDocumentService.complete_grn(grn_excess)

        # Stock remains unchanged at 90
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("90.00"))

    def test_full_business_flow_end_to_end(self):
        # 1. Supplier
        supplier = self.supplier_a

        # 2. Purchase Order for 100 Laptops
        po = PurchaseService.create_purchase_order(
            organization=self.org_a,
            supplier=supplier,
            warehouse=self.wh_a,
            items_data=[{"product": self.laptop, "quantity": Decimal("100.00"), "unit_cost": Decimal("400000.00")}],
            user=self.user_a
        )
        self.assertEqual(po.subtotal, Decimal("40000000.00"))

        # 3. Approve PO
        PurchaseService.approve_purchase_order(po)

        # 4. GRN 1: 40 Laptops
        grn1 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("40.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn1)
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("40.00"))

        # 5. GRN 2: 60 Laptops
        grn2 = InventoryDocumentService.create_grn(
            organization=self.org_a,
            warehouse=self.wh_a,
            received_date=timezone.now().date(),
            items_data=[{"product": self.laptop, "quantity": Decimal("60.00"), "unit_cost": Decimal("400000.00")}],
            purchase_order=po,
            user=self.user_a
        )
        InventoryDocumentService.complete_grn(grn2)

        # Final Verification
        po.refresh_from_db()
        po_item = po.items.get(product=self.laptop)

        self.assertEqual(po_item.quantity, Decimal("100.00"))
        self.assertEqual(po_item.received_quantity, Decimal("100.00"))
        self.assertEqual(po_item.remaining_quantity, Decimal("0.00"))
        self.assertEqual(po.status, "RECEIVED")
        self.assertEqual(StockService.get_balance(self.laptop, warehouse=self.wh_a), Decimal("100.00"))

    def test_api_supplier_and_purchase_order_endpoints(self):
        self.client.force_authenticate(user=self.user_a)

        # GET /api/v1/suppliers/
        res_sup = self.client.get("/api/v1/suppliers/")
        self.assertEqual(res_sup.status_code, status.HTTP_200_OK)

        # POST /api/v1/purchase-orders/
        po_payload = {
            "supplier": self.supplier_a.id,
            "warehouse": self.wh_a.id,
            "order_date": str(timezone.now().date()),
            "items": [
                {"product": self.laptop.id, "quantity": "10.00", "unit_cost": "400000.00"}
            ]
        }
        res_po = self.client.post("/api/v1/purchase-orders/", data=po_payload, format="json")
        self.assertEqual(res_po.status_code, status.HTTP_201_CREATED)
        po_id = res_po.data["data"]["id"]

        # POST /api/v1/purchase-orders/<id>/submit/
        res_submit = self.client.post(f"/api/v1/purchase-orders/{po_id}/submit/")
        self.assertEqual(res_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(res_submit.data["data"]["status"], "SUBMITTED")

        # POST /api/v1/purchase-orders/<id>/approve/
        res_approve = self.client.post(f"/api/v1/purchase-orders/{po_id}/approve/")
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(res_approve.data["data"]["status"], "APPROVED")
