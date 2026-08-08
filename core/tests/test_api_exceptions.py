from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, UserProfile, Invoice
from core.exceptions.business import PaymentExceedsBalance, InvoiceAlreadyPaid, InvalidQuotationStatus

User = get_user_model()


class APIExceptionsTestCase(TestCase):

    def setUp(self):
        # Organization setup
        self.org = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet-ventures")
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="STAFF")

        # Customer setup
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Test Customer Ltd",
            email="customer@test.com"
        )

        # Invoice setup
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-999",
            invoice_date="2026-08-08",
            due_date="2026-09-08",
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )

        # User without organization
        self.no_org_user = User.objects.create_user(username="noorguser", password="password123")

        self.client = APIClient()

    def test_404_not_found_standard_response(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/customers/999999/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertIn("not_found", response.data["code"])
        self.assertEqual(response.data["errors"], {})

    def test_validation_error_standard_response(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "company_name": "",
            "email": "invalid-email"
        }
        response = self.client.post("/api/v1/customers/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Validation failed.")
        self.assertIn("company_name", response.data["errors"])
        self.assertIn("email", response.data["errors"])

    def test_business_rule_exception_overpayment(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "invoice": self.invoice.id,
            "amount": "150000.00",
            "payment_method": "BANK"
        }
        response = self.client.post("/api/v1/payments/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "payment_exceeds_balance")
        self.assertEqual(response.data["message"], "Payment amount exceeds the outstanding balance.")

    def test_unauthenticated_request_response(self):
        self.client.logout()
        response = self.client.get("/api/v1/customers/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertIn("not_authenticated", response.data["code"])

    def test_forbidden_user_without_organization_response(self):
        self.client.force_authenticate(user=self.no_org_user)
        response = self.client.get("/api/v1/customers/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertIn("permission_denied", response.data["code"])
