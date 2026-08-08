from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, UserProfile
from inventory.models import Warehouse, WarehouseLocation, InventoryItem, StockMovement

User = get_user_model()


class InventoryAPITestCase(TestCase):

    def setUp(self):
        # Organization A Setup
        self.org_a = Organization.objects.create(name="ArewaNet Logistics", slug="arewanet-logistics")
        self.user_a = User.objects.create_user(username="invusera", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Networking Equipment")
        self.prod_a = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Enterprise Switch 24-Port",
            sku="SW-24P",
            selling_price=Decimal("250000.00")
        )

        self.wh_a1 = Warehouse.objects.create(organization=self.org_a, name="Kano Main Depot", code="WH-KNO")
        self.wh_a2 = Warehouse.objects.create(organization=self.org_a, name="Abuja Branch Hub", code="WH-ABJ")
        self.loc_a1 = WarehouseLocation.objects.create(warehouse=self.wh_a1, name="Rack Alpha", code="RACK-A")

        # Organization B Setup
        self.org_b = Organization.objects.create(name="Sahara Telecoms", slug="sahara-telecoms")
        self.user_b = User.objects.create_user(username="invuserb", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Sahara Warehouse", code="WH-SAHARA")

        self.client = APIClient()

    def test_warehouse_api_crud(self):
        self.client.force_authenticate(user=self.user_a)

        # Create Warehouse
        response = self.client.post("/api/v1/inventory/warehouses/", {
            "name": "Kaduna Express Depot",
            "code": "WH-KDA",
            "address": "Expressway layout, Kaduna"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["code"], "WH-KDA")

        # List Warehouses
        list_resp = self.client.get("/api/v1/inventory/warehouses/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_resp.data["data"]), 3)

    def test_stock_receive_api_endpoint(self):
        self.client.force_authenticate(user=self.user_a)

        payload = {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "location": self.loc_a1.id,
            "quantity": "100.00",
            "reference_type": "PURCHASE_ORDER",
            "reference_id": 45,
            "notes": "Initial delivery from vendor"
        }

        response = self.client.post("/api/v1/inventory/receive/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(Decimal(str(response.data["data"]["balance"])), Decimal("100.00"))

    def test_stock_issue_api_and_insufficient_stock_rejection(self):
        self.client.force_authenticate(user=self.user_a)

        # Initial receive 5 units
        self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "5.00"
        }, format="json")

        # Valid issue 2 units
        issue_resp = self.client.post("/api/v1/inventory/issue/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "2.00"
        }, format="json")
        self.assertEqual(issue_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(issue_resp.data["data"]["balance"])), Decimal("3.00"))

        # Over-issue attempt (try issuing 10 units when balance is 3)
        fail_resp = self.client.post("/api/v1/inventory/issue/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "10.00"
        }, format="json")

        self.assertEqual(fail_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(fail_resp.data["success"])
        self.assertEqual(fail_resp.data["code"], "insufficient_stock")

        # Verify balance remains 3.00
        balance_resp = self.client.get(f"/api/v1/inventory/?product={self.prod_a.id}&warehouse={self.wh_a1.id}")
        self.assertEqual(balance_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(balance_resp.data["data"][0]["quantity"])), Decimal("3.00"))

    def test_stock_adjustment_api_endpoint(self):
        self.client.force_authenticate(user=self.user_a)

        # Receive 100
        self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "100.00"
        }, format="json")

        # Adjust balance to 105
        adj_resp = self.client.post("/api/v1/inventory/adjust/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "105.00",
            "notes": "Physical count reconciliation"
        }, format="json")
        self.assertEqual(adj_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(adj_resp.data["data"]["new_balance"])), Decimal("105.00"))

    def test_stock_transfer_api_endpoint(self):
        self.client.force_authenticate(user=self.user_a)

        # Receive 100 in Main Depot, 50 in Branch Depot
        self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "100.00"
        }, format="json")
        self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a2.id,
            "quantity": "50.00"
        }, format="json")

        # Transfer 20 from WH1 to WH2
        transfer_resp = self.client.post("/api/v1/inventory/transfer/", {
            "product": self.prod_a.id,
            "from_warehouse": self.wh_a1.id,
            "to_warehouse": self.wh_a2.id,
            "quantity": "20.00",
            "notes": "Stock rebalancing"
        }, format="json")

        self.assertEqual(transfer_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(transfer_resp.data["data"]["source_balance"])), Decimal("80.00"))
        self.assertEqual(Decimal(str(transfer_resp.data["data"]["destination_balance"])), Decimal("70.00"))

    def test_multi_tenant_inventory_isolation(self):
        self.client.force_authenticate(user=self.user_a)

        # Attempt to receive stock for Org B warehouse using Org A credentials
        response = self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_b.id,
            "quantity": "50.00"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_critical_multi_step_inventory_audit_workflow(self):
        """
        Sprint 7.2 Integration Test:
        Receive 100 -> Issue 20 -> Adjust +5 (to 85) -> Transfer 15 -> Balance 70
        And verify Stock Movements history API returns exact ledger logs.
        """
        self.client.force_authenticate(user=self.user_a)

        # 1. Receive 100
        self.client.post("/api/v1/inventory/receive/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "100.00"
        }, format="json")

        # 2. Issue 20
        self.client.post("/api/v1/inventory/issue/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "20.00",
            "reference_type": "SALE",
            "reference_id": 201
        }, format="json")

        # 3. Adjust to 85 (+5)
        self.client.post("/api/v1/inventory/adjust/", {
            "product": self.prod_a.id,
            "warehouse": self.wh_a1.id,
            "quantity": "85.00"
        }, format="json")

        # 4. Transfer 15 to Branch Depot
        self.client.post("/api/v1/inventory/transfer/", {
            "product": self.prod_a.id,
            "from_warehouse": self.wh_a1.id,
            "to_warehouse": self.wh_a2.id,
            "quantity": "15.00"
        }, format="json")

        # Expected Final Balance at Main Depot: 100 - 20 + 5 - 15 = 70.00
        bal_resp = self.client.get(f"/api/v1/inventory/?product={self.prod_a.id}&warehouse={self.wh_a1.id}")
        self.assertEqual(bal_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(bal_resp.data["data"][0]["quantity"])), Decimal("70.00"))

        # Verify Stock Movement History API
        history_resp = self.client.get(f"/api/v1/inventory/stock-movements/?product={self.prod_a.id}")
        self.assertEqual(history_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(history_resp.data["data"]), 4)
