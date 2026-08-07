from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Product, Invoice, InvoiceItem, UserProfile

User = get_user_model()


class InvoiceAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="invadmin", password="password")
        self.org = Organization.objects.create(name="Invoice Test Org", slug="inv-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Northern Telecoms",
            email="info@northerntel.com",
            phone="08022223333"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Fibre Setup",
            selling_price=Decimal("250000.00")
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-8888",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("250000.00"),
            total_due=Decimal("250000.00"),
            status="UNPAID"
        )
        self.item = InvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            description="Installation",
            qty=Decimal("1.00"),
            unit_price=Decimal("250000.00"),
            total=Decimal("250000.00")
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_invoice(self):
        response = self.client.post("/api/v1/invoices/", {
            "customer": self.customer.id,
            "invoice_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=7)),
            "items": [
                {"product": self.product.id, "description": "Support", "qty": "2", "unit_price": "50000.00"}
            ]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["invoice_no"].startswith("INV-"))

    def test_update_invoice(self):
        response = self.client.patch(f"/api/v1/invoices/{self.invoice.id}/", {
            "payment_reference": "Ref-Updated-123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["payment_reference"], "Ref-Updated-123")

    def test_delete_invoice(self):
        inv = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-TEMP-99",
            invoice_date=date.today(),
            due_date=date.today(),
            total_due=Decimal("1000.00")
        )
        response = self.client.delete(f"/api/v1/invoices/{inv.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Invoice.objects.filter(id=inv.id).exists())

    def test_invoice_pdf(self):
        response = self.client.get(f"/api/v1/invoices/{self.invoice.id}/pdf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_public_invoice(self):
        self.client.logout()
        token = self.invoice.public_token
        response = self.client.get(f"/api/v1/invoices/public/{token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["invoice_no"], "INV-2026-8888")

    def test_pay_invoice(self):
        response = self.client.post(f"/api/v1/invoices/{self.invoice.id}/pay/", {
            "amount": "100000.00",
            "method": "BANK_TRANSFER",
            "reference": "TRX-API-888"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["invoice_status"], "PARTIAL")

    def test_invoice_payments_history(self):
        self.client.post(f"/api/v1/invoices/{self.invoice.id}/pay/", {
            "amount": "50000.00",
            "method": "CASH"
        })
        response = self.client.get(f"/api/v1/invoices/{self.invoice.id}/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["data"]), 0)

    def test_invoice_timeline(self):
        response = self.client.get(f"/api/v1/invoices/{self.invoice.id}/timeline/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"], list)

    def test_invoice_balance(self):
        response = self.client.get(f"/api/v1/invoices/{self.invoice.id}/balance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["data"]["invoice"])), Decimal("250000.00"))

    def test_email_invoice(self):
        response = self.client.post(f"/api/v1/invoices/{self.invoice.id}/email/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_duplicate_invoice(self):
        response = self.client.post(f"/api/v1/invoices/{self.invoice.id}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["data"]["id"], self.invoice.id)
        self.assertEqual(response.data["data"]["status"], "DRAFT")

    def test_invoice_dashboard(self):
        response = self.client.get("/api/v1/invoices/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("unpaid", response.data["data"])
        self.assertIn("outstanding", response.data["data"])

    def test_organization_isolation(self):
        other_user = User.objects.create_user(username="otherinvuser", password="password")
        other_org = Organization.objects.create(name="Other Invoice Org", slug="other-inv-org")
        UserProfile.objects.create(user=other_user, organization=other_org, role="ADMIN")

        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/v1/invoices/{self.invoice.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
