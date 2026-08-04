import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, Customer, Product
from sales.models import Invoice, InvoiceItem, Quotation, QuotationItem, Payment, ActivityLog
from sales.services import DocumentNumberService, InvoiceCalculator, ExportService
from sales.mixins import TotalsMixin
from sales.utils import log_activity
from sales.forms import InvoiceForm, QuotationForm

User = get_user_model()


class MockItem:
    def __init__(self, qty, unit_price):
        self.qty = qty
        self.unit_price = unit_price


class DocumentNumberServiceTest(TestCase):
    def test_document_number_generation(self):
        inv_no = DocumentNumberService.generate("invoice", 1)
        self.assertTrue(inv_no.startswith("INV-"))
        self.assertTrue(inv_no.endswith("-0001"))

        qtn_no = DocumentNumberService.generate("quotation", 42)
        self.assertTrue(qtn_no.startswith("QTN-"))
        self.assertTrue(qtn_no.endswith("-0042"))

        rct_no = DocumentNumberService.generate("receipt", 100)
        self.assertTrue(rct_no.startswith("RCT-"))
        self.assertTrue(rct_no.endswith("-0100"))

        custom_no = DocumentNumberService.generate("unknown", 5)
        self.assertTrue(custom_no.startswith("DOC-"))


class InvoiceCalculatorTest(TestCase):
    def test_calculate_totals(self):
        items = [
            MockItem(qty=2, unit_price=Decimal("5000.00")),
            MockItem(qty=1, unit_price=Decimal("10000.00")),
        ]
        result = InvoiceCalculator.calculate(items, vat=7.5, discount=1000)

        self.assertEqual(result["subtotal"], Decimal("20000.00"))
        self.assertEqual(result["vat"], Decimal("1500.00"))
        self.assertEqual(result["discount"], Decimal("1000"))
        self.assertEqual(result["total"], Decimal("20500.00"))


class SalesDomainModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="salesadmin", password="password")
        self.org = Organization.objects.create(
            name="ArewaNet Ltd",
            email="sales@arewanet.com",
            phone="08012345678",
            address="Kano, Nigeria"
        )
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Acme Corp",
            email="info@acme.com",
            phone="08099887766",
            address="Abuja, Nigeria"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Web Design Service",
            selling_price=Decimal("250000.00")
        )

    def test_sales_invoice_and_items(self):
        invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            document_number="INV-2026-0001",
            issue_date=datetime.date.today(),
            status="DRAFT"
        )
        item = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            description="Corporate website setup",
            quantity=Decimal("1.00"),
            unit_price=Decimal("250000.00")
        )
        self.assertEqual(item.total, Decimal("250000.00"))
        self.assertEqual(str(invoice), "Invoice INV-2026-0001")

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("100000.00"),
            payment_date=datetime.date.today(),
            payment_method="BANK",
            reference="TRX-101"
        )
        self.assertEqual(invoice.payments.count(), 1)
        self.assertTrue("Payment ₦100000.00" in str(payment))

    def test_sales_quotation_and_items(self):
        quotation = Quotation.objects.create(
            organization=self.org,
            customer=self.customer,
            document_number="QTN-2026-0001",
            issue_date=datetime.date.today(),
            expiry_date=datetime.date.today() + datetime.timedelta(days=14),
            status="DRAFT"
        )
        item = QuotationItem.objects.create(
            quotation=quotation,
            product=self.product,
            description="Enterprise Portal Setup",
            quantity=Decimal("2.00"),
            unit_price=Decimal("150000.00")
        )
        self.assertEqual(item.total, Decimal("300000.00"))
        self.assertEqual(str(quotation), "Quotation QTN-2026-0001")

    def test_activity_logging_helper(self):
        invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            document_number="INV-2026-0002",
            issue_date=datetime.date.today()
        )
        log = log_activity(self.user, invoice, "PRINT", "Printed customer copy")
        self.assertEqual(log.document_type, "Invoice")
        self.assertEqual(log.action, "PRINT")
        self.assertEqual(ActivityLog.objects.count(), 1)

    def test_forms_validation(self):
        form = InvoiceForm(data={
            "customer": self.customer.pk,
            "document_number": "INV-2026-0003",
            "issue_date": "2026-08-04",
            "status": "DRAFT",
            "notes": "Test note",
            "vat": "18750.00"
        }, organization=self.org)
        self.assertTrue(form.is_valid())
        inv = form.save()
        self.assertEqual(inv.organization, self.org)
