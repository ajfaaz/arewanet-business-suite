from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Invoice, Product, Quotation, UserProfile, ActivityLog
from sales.payments.models import Payment

User = get_user_model()


class DashboardAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="dashadmin", password="password")
        self.org = Organization.objects.create(name="Dashboard Test Org", slug="dash-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Kano Enterprises",
            email="kano@ent.com",
            phone="08022221111"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Cloud Server",
            sku="CLOUD-01",
            selling_price=Decimal("120000.00")
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-8888",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=15),
            subtotal=Decimal("120000.00"),
            total_due=Decimal("120000.00"),
            status="UNPAID"
        )
        self.payment = Payment.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice=self.invoice,
            receipt_number="RCP-2026-8888",
            amount=Decimal("60000.00"),
            payment_method="BANK",
            payment_date=date.today(),
            status="COMPLETED"
        )
        ActivityLog.objects.create(
            user=self.user,
            action="Invoice INV-2026-8888 created"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_dashboard_summary_endpoint(self):
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertIn("sales_today", data)
        self.assertIn("outstanding", data)
        self.assertEqual(data["customers"], 1)

    def test_revenue_trend_endpoint(self):
        response = self.client.get("/api/v1/dashboard/revenue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)

    def test_receivables_endpoint(self):
        response = self.client.get("/api/v1/dashboard/receivables/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("current", response.data["data"])
        self.assertIn("30_days", response.data["data"])

    def test_top_customers_endpoint(self):
        response = self.client.get("/api/v1/dashboard/top-customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)

    def test_top_products_endpoint(self):
        response = self.client.get("/api/v1/dashboard/top-products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)

    def test_activity_feed_endpoint(self):
        response = self.client.get("/api/v1/dashboard/activity/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)

    def test_notifications_summary_endpoint(self):
        response = self.client.get("/api/v1/dashboard/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertIn("overdue_invoices", data)
        self.assertIn("expiring_quotations", data)
        self.assertIn("subscriptions_due", data)

    def test_organization_isolation(self):
        other_user = User.objects.create_user(username="otherdashuser", password="password")
        other_org = Organization.objects.create(name="Other Dash Org", slug="other-dash-org")
        UserProfile.objects.create(user=other_user, organization=other_org, role="ADMIN")

        self.client.force_authenticate(user=other_user)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["customers"], 0)
        self.assertEqual(data["invoices"], 0)
