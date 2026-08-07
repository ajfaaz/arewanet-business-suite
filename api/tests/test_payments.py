from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Invoice, UserProfile
from sales.payments.models import Payment

User = get_user_model()


class PaymentAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="pmtadmin", password="password")
        self.org = Organization.objects.create(name="Payment Test Org", slug="pmt-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Arewa Retailers Ltd",
            email="retail@arewa.com",
            phone="08099990000"
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-7777",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("150000.00"),
            total_due=Decimal("150000.00"),
            status="UNPAID"
        )
        self.payment = Payment.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice=self.invoice,
            receipt_number="RCP-2026-7777",
            amount=Decimal("50000.00"),
            payment_method="BANK",
            payment_date=date.today(),
            status="COMPLETED"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_receive_payment_success(self):
        inv = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-7778",
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )
        response = self.client.post("/api/v1/payments/", {
            "customer": self.customer.id,
            "invoice": inv.id,
            "amount": "50000.00",
            "payment_method": "CASH",
            "reference": "TRX-CASH-001"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PARTIAL")

    def test_overpayment_prevention(self):
        response = self.client.post("/api/v1/payments/", {
            "invoice": self.invoice.id,
            "amount": "500000.00",
            "payment_method": "BANK"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_reverse_payment(self):
        response = self.client.post(f"/api/v1/payments/{self.payment.id}/reverse/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "REVERSED")

    def test_receipt_pdf(self):
        response = self.client.get(f"/api/v1/payments/{self.payment.id}/receipt/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_timeline(self):
        response = self.client.get(f"/api/v1/payments/{self.payment.id}/timeline/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"], list)

    def test_payment_dashboard(self):
        response = self.client.get("/api/v1/payments/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("today", response.data["data"])
        self.assertIn("month", response.data["data"])

    def test_payment_analytics(self):
        response = self.client.get("/api/v1/payments/analytics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("bank", response.data["data"])

    def test_email_receipt(self):
        response = self.client.post(f"/api/v1/payments/{self.payment.id}/email/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_organization_isolation(self):
        other_user = User.objects.create_user(username="otherpmtuser", password="password")
        other_org = Organization.objects.create(name="Other Payment Org", slug="other-pmt-org")
        UserProfile.objects.create(user=other_user, organization=other_org, role="ADMIN")

        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/v1/payments/{self.payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
