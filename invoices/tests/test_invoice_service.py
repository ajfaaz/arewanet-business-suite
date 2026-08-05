from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError

from invoices.models import Organization, Customer, Invoice, InvoiceItem
from invoices.services.invoice_service import InvoiceService

class InvoiceServiceTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="ArewaNet Test Org", slug="arewanet-test-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Acme Corp",
            email="acme@example.com"
        )

    def test_calculate_subtotal(self):
        item1 = InvoiceItem(qty=2, unit_price=Decimal("15000.00"))
        item2 = InvoiceItem(qty=1, unit_price=Decimal("50000.00"))
        subtotal = InvoiceService.calculate_subtotal([item1, item2])
        self.assertEqual(subtotal, Decimal("80000.00"))

    def test_calculate_vat_and_total(self):
        subtotal = Decimal("100000.00")
        vat_amount = InvoiceService.calculate_vat(subtotal, Decimal("7.50"))
        total = InvoiceService.calculate_total(subtotal, vat_amount)
        self.assertEqual(vat_amount, Decimal("7500.00"))
        self.assertEqual(total, Decimal("107500.00"))

    def test_create_invoice_success(self):
        invoice = Invoice(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            vat=Decimal("7.50")
        )
        items = [
            InvoiceItem(description="Cloud Hosting Setup", qty=1, unit_price=Decimal("100000.00")),
            InvoiceItem(description="Domain Registration", qty=2, unit_price=Decimal("5000.00"))
        ]

        created_invoice = InvoiceService.create_invoice(invoice, items)
        self.assertIsNotNone(created_invoice.pk)
        self.assertEqual(created_invoice.subtotal, Decimal("110000.00"))
        self.assertEqual(created_invoice.total_due, Decimal("118250.00"))
        self.assertEqual(created_invoice.items.count(), 2)

    def test_validation_due_date_before_invoice_date(self):
        invoice = Invoice(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today() - timedelta(days=1)
        )
        items = [InvoiceItem(description="Test", qty=1, unit_price=Decimal("100.00"))]
        with self.assertRaises(ValidationError):
            InvoiceService.create_invoice(invoice, items)

    def test_validation_empty_items(self):
        invoice = Invoice(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=7)
        )
        with self.assertRaises(ValidationError):
            InvoiceService.create_invoice(invoice, [])
