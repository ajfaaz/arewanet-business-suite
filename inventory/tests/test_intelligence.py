from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Product, ProductCategory, UserProfile
from inventory.models import Warehouse, StockAlert, StockMovement
from inventory.services import StockService
from inventory.intelligence_services import (
    StockLevelService,
    StockAlertService,
    InventoryValuationService,
    InventoryAnalyticsSelector,
)

User = get_user_model()


class InventoryIntelligenceTestCase(TestCase):

    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(name="Org A Logistics", slug="org-a-logistics")
        self.user_a = User.objects.create_user(username="inteluser_a", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")
        self.wh_a = Warehouse.objects.create(organization=self.org_a, name="Main Warehouse A", code="WH-A")

        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Gadgets")

        # Product with thresholds
        self.laptop = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="MacBook Pro 16",
            sku="MBP-16",
            selling_price=Decimal("1500000.00"),
            cost_price=Decimal("1200000.00"),
            is_stockable=True,
            minimum_stock=Decimal("5.00"),
            reorder_level=Decimal("10.00"),
            maximum_stock=Decimal("50.00")
        )

        self.mouse = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="Logitech MX Master",
            sku="MX-MST",
            selling_price=Decimal("80000.00"),
            cost_price=Decimal("60000.00"),
            is_stockable=True,
            minimum_stock=Decimal("10.00"),
            reorder_level=Decimal("20.00"),
            maximum_stock=Decimal("100.00")
        )

        # Organization B (Tenant Isolation test)
        self.org_b = Organization.objects.create(name="Org B Traders", slug="org-b-traders")
        self.user_b = User.objects.create_user(username="inteluser_b", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")
        self.wh_b = Warehouse.objects.create(organization=self.org_b, name="Main Warehouse B", code="WH-B")

        self.client = APIClient()

    def test_stock_level_status_determination(self):
        # 0 -> OUT_OF_STOCK
        status_0 = StockLevelService.get_status(self.laptop, current_quantity=Decimal("0.00"))
        self.assertEqual(status_0, "OUT_OF_STOCK")

        # 5 -> LOW_STOCK (reorder_level=10)
        status_5 = StockLevelService.get_status(self.laptop, current_quantity=Decimal("5.00"))
        self.assertEqual(status_5, "LOW_STOCK")

        # 20 -> NORMAL (reorder_level=10, max=50)
        status_20 = StockLevelService.get_status(self.laptop, current_quantity=Decimal("20.00"))
        self.assertEqual(status_20, "NORMAL")

        # 60 -> OVERSTOCK (max=50)
        status_60 = StockLevelService.get_status(self.laptop, current_quantity=Decimal("60.00"))
        self.assertEqual(status_60, "OVERSTOCK")

    def test_alert_creation_and_auto_resolution_lifecycle(self):
        # 1. Receive 5 laptops (reorder level = 10) -> LOW_STOCK
        StockService.receive(self.laptop, self.wh_a, quantity=Decimal("5.00"))

        alert = StockAlert.objects.filter(organization=self.org_a, product=self.laptop, is_resolved=False).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, "LOW_STOCK")
        self.assertEqual(alert.current_quantity, Decimal("5.00"))

        # 2. Receive 30 more laptops (Total = 35, reorder level = 10, max = 50) -> NORMAL
        StockService.receive(self.laptop, self.wh_a, quantity=Decimal("30.00"))

        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)
        self.assertIsNotNone(alert.resolved_at)

        active_alerts = StockAlert.objects.filter(organization=self.org_a, product=self.laptop, is_resolved=False)
        self.assertEqual(active_alerts.count(), 0)

    def test_inventory_valuation(self):
        # 10 Laptops @ cost 1,200,000 = 12,000,000
        StockService.receive(self.laptop, self.wh_a, quantity=Decimal("10.00"))
        # 50 Mice @ cost 60,000 = 3,000,000
        StockService.receive(self.mouse, self.wh_a, quantity=Decimal("50.00"))

        total_value = InventoryValuationService.get_value(self.org_a)
        self.assertEqual(total_value, Decimal("15000000.00"))

    def test_reorder_recommendations(self):
        # Laptop stock = 8 (reorder = 10, max = 50) -> recommended = 42
        StockService.receive(self.laptop, self.wh_a, quantity=Decimal("8.00"))

        recs = InventoryAnalyticsSelector.get_reorder_recommendations(self.org_a)
        self.assertEqual(len(recs), 2) # Both Laptop (8) and Mouse (0) are low/out of stock

        laptop_rec = next(r for r in recs if r["product_id"] == self.laptop.id)
        self.assertEqual(laptop_rec["recommended_quantity"], "42.00")

    def test_dashboard_api_endpoints_and_tenant_isolation(self):
        self.client.force_authenticate(user=self.user_a)

        # Receive stock
        StockService.receive(self.laptop, self.wh_a, quantity=Decimal("8.00"))

        # GET /api/v1/inventory/dashboard/
        res_dash = self.client.get("/api/v1/inventory/dashboard/")
        self.assertEqual(res_dash.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dash.data["data"]["products"]["total"], 2)

        # GET /api/v1/inventory/statistics/
        res_stats = self.client.get("/api/v1/inventory/statistics/")
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        self.assertEqual(res_stats.data["data"]["stock_in"], "8.00")

        # GET /api/v1/inventory/top-products/
        res_top = self.client.get("/api/v1/inventory/top-products/")
        self.assertEqual(res_top.status_code, status.HTTP_200_OK)

        # GET /api/v1/inventory/slow-moving/
        res_slow = self.client.get("/api/v1/inventory/slow-moving/")
        self.assertEqual(res_slow.status_code, status.HTTP_200_OK)

        # GET /api/v1/inventory/alerts/
        res_alerts = self.client.get("/api/v1/inventory/alerts/")
        self.assertEqual(res_alerts.status_code, status.HTTP_200_OK)
        alerts_list = res_alerts.data.get("data") if isinstance(res_alerts.data, dict) and "data" in res_alerts.data else res_alerts.data
        self.assertGreaterEqual(len(alerts_list), 1)

        # GET /api/v1/inventory/reorder-recommendations/
        res_reorder = self.client.get("/api/v1/inventory/reorder-recommendations/")
        self.assertEqual(res_reorder.status_code, status.HTTP_200_OK)

        # Tenant B cannot see Tenant A's data
        self.client.force_authenticate(user=self.user_b)
        res_dash_b = self.client.get("/api/v1/inventory/dashboard/")
        self.assertEqual(res_dash_b.data["data"]["products"]["total"], 0)
        self.assertEqual(res_dash_b.data["data"]["stock"]["total_units"], "0.00")
