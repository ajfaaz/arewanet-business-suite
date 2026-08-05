from decimal import Decimal
from datetime import date
from django.test import TestCase
from invoices.models import Organization, Customer, Invoice
from invoices.services.payment_service import PaymentService

class PaymentServiceTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="ArewaNet Test Org 2", slug="arewanet-test-org-2")
        self.customer = Customer.objects.create(organization=self.org, company_name="Beta Ltd")
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )

    def test_record_partial_payment(self):
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("40000.00"),
            payment_method="BANK",
            notes="Partial payment via Bank Transfer"
        )
        self.assertIsNotNone(payment.pk)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PARTIAL")

    def test_record_full_payment(self):
        PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("100000.00"),
            payment_method="POS",
            notes="Full payment via POS"
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")
