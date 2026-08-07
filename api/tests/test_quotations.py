from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Quotation, Product, UserProfile

User = get_user_model()


class QuotationAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="qtnadmin", password="password")
        self.org = Organization.objects.create(name="Quotation Test Org", slug="qtn-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Northern Telecoms Ltd",
            email="telecoms@northern.com",
            phone="08033334444"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Network Audit",
            sku="NET-AUD-01",
            selling_price=Decimal("250000.00")
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            customer=self.customer,
            quotation_no="QTN-2026-9999",
            quotation_date=date.today(),
            valid_until=date.today() + timedelta(days=30),
            subtotal=Decimal("250000.00"),
            total=Decimal("250000.00"),
            status="DRAFT"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_quotations(self):
        response = self.client.get("/api/v1/quotations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_create_quotation(self):
        response = self.client.post("/api/v1/quotations/", {
            "customer": self.customer.id,
            "quotation_date": str(date.today()),
            "valid_until": str(date.today() + timedelta(days=14)),
            "items": [
                {"product": self.product.id, "description": "Audit Service", "qty": "1", "unit_price": "250000.00"}
            ]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])

    def test_approve_quotation(self):
        response = self.client.post(f"/api/v1/quotations/{self.quotation.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, "APPROVED")

    def test_reject_quotation(self):
        response = self.client.post(f"/api/v1/quotations/{self.quotation.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, "REJECTED")

    def test_convert_to_invoice(self):
        response = self.client.post(f"/api/v1/quotations/{self.quotation.id}/convert/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, "CONVERTED")

    def test_quotation_pdf(self):
        response = self.client.get(f"/api/v1/quotations/{self.quotation.id}/pdf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_email_quotation(self):
        response = self.client.post(f"/api/v1/quotations/{self.quotation.id}/email/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_quotation_dashboard(self):
        response = self.client.get("/api/v1/quotations/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("draft", response.data["data"])
        self.assertIn("total_count", response.data["data"])
