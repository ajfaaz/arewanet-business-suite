import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, Customer, Product, Invoice as MainInvoice
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

        main_inv = MainInvoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-0001",
            invoice_date=datetime.date.today(),
            due_date=datetime.date.today(),
            project_name="Corporate website setup",
            deployment_phase="Phase 1"
        )
        payment = Payment.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice=main_inv,
            receipt_number="RCP-TRX-101",
            amount=Decimal("100000.00"),
            payment_date=datetime.date.today(),
            payment_method="BANK",
            reference="TRX-101"
        )
        self.assertEqual(main_inv.payments.count(), 1)
        self.assertTrue("100,000.00" in str(payment))

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


import io
from sales.models import CreditNote, DebitNote
from sales.services import CreditNoteService, DebitNoteService, StatementService, AgingService
from core.choices import CreditNoteStatus, DebitNoteStatus
from core.documents.pdf_service import PDFService

class FinancialDocumentsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_fin", password="password")
        self.org = Organization.objects.create(name="ArewaNet Test Org", slug="arewanet-test-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Acme Limited",
            email="info@acme.com",
            phone="08012345678"
        )
        self.invoice = MainInvoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-0001",
            invoice_date=datetime.date.today() - datetime.timedelta(days=40),
            due_date=datetime.date.today() - datetime.timedelta(days=10),
            project_name="ERP Setup",
            deployment_phase="Phase 1",
            subtotal=Decimal("100000.00"),
            vat=Decimal("0.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )

    def test_credit_note_workflow(self):
        cn = CreditNoteService.issue_credit_note(
            organization=self.org,
            invoice=self.invoice,
            amount=Decimal("20000.00"),
            reason="Item Return Discount",
            user=self.user
        )

        self.assertEqual(cn.status, CreditNoteStatus.ISSUED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_credit_notes, Decimal("20000.00"))
        self.assertEqual(self.invoice.effective_total_due, Decimal("80000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("80000.00"))

        CreditNoteService.cancel_credit_note(cn, user=self.user)
        cn.refresh_from_db()
        self.assertEqual(cn.status, CreditNoteStatus.CANCELLED)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_credit_notes, Decimal("0.00"))
        self.assertEqual(self.invoice.effective_total_due, Decimal("100000.00"))

    def test_debit_note_workflow(self):
        dn = DebitNoteService.issue_debit_note(
            organization=self.org,
            invoice=self.invoice,
            amount=Decimal("15000.00"),
            reason="Additional Onsite Support",
            user=self.user
        )

        self.assertEqual(dn.status, DebitNoteStatus.ISSUED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_debit_notes, Decimal("15000.00"))
        self.assertEqual(self.invoice.effective_total_due, Decimal("115000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("115000.00"))

    def test_customer_statement(self):
        cn = CreditNoteService.issue_credit_note(
            organization=self.org,
            invoice=self.invoice,
            amount=Decimal("10000.00"),
            reason="Early Payment Rebate",
            user=self.user
        )

        stmt = StatementService.generate_statement(self.customer)
        self.assertEqual(stmt['customer'], self.customer)
        self.assertGreater(len(stmt['transactions']), 0)
        self.assertEqual(stmt['closing_balance'], Decimal("90000.00"))

    def test_aging_report(self):
        summary = AgingService.get_aging_summary(self.org)
        self.assertEqual(summary['total_outstanding'], Decimal("100000.00"))
        self.assertEqual(summary['current'], Decimal("100000.00"))

    def test_pdf_generation(self):
        cn = CreditNoteService.issue_credit_note(
            organization=self.org,
            invoice=self.invoice,
            amount=Decimal("5000.00"),
            reason="Adjustment",
            user=self.user
        )

        buf = io.BytesIO()
        PDFService.generate_credit_note(cn, buf)
        self.assertTrue(buf.getvalue().startswith(b'%PDF'))

        buf_dn = io.BytesIO()
        dn = DebitNoteService.issue_debit_note(
            organization=self.org,
            invoice=self.invoice,
            amount=Decimal("2000.00"),
            reason="Extra Charge",
            user=self.user
        )
        PDFService.generate_debit_note(dn, buf_dn)
        self.assertTrue(buf_dn.getvalue().startswith(b'%PDF'))

        buf_stmt = io.BytesIO()
        stmt = StatementService.generate_statement(self.customer)
        PDFService.generate_statement(stmt, buf_stmt)
        self.assertTrue(buf_stmt.getvalue().startswith(b'%PDF'))


from django.core.management import call_command
from sales.subscriptions.models import SubscriptionTemplate, Subscription, SubscriptionItem
from sales.subscriptions.services import SubscriptionService
from core.choices import BillingCycle, SubscriptionStatus

class SubscriptionWorkflowTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="subadmin", password="password")
        self.org = Organization.objects.create(name="ArewaNet Sub Org", slug="arewanet-sub-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="SaaS Client Ltd",
            email="client@saas.com"
        )
        self.template = SubscriptionTemplate.objects.create(
            organization=self.org,
            title="Monthly Support Package",
            billing_cycle=BillingCycle.MONTHLY,
            description="Standard ICT Support"
        )

    def test_next_billing_date_calculations(self):
        start = datetime.date(2026, 1, 31)
        next_m = SubscriptionService.next_billing_date(start, BillingCycle.MONTHLY)
        self.assertEqual(next_m, datetime.date(2026, 2, 28))

        next_q = SubscriptionService.next_billing_date(datetime.date(2026, 1, 1), BillingCycle.QUARTERLY)
        self.assertEqual(next_q, datetime.date(2026, 4, 1))

        next_a = SubscriptionService.next_billing_date(datetime.date(2026, 1, 1), BillingCycle.ANNUAL)
        self.assertEqual(next_a, datetime.date(2027, 1, 1))

    def test_subscription_creation_and_mrr(self):
        sub = SubscriptionService.create_subscription(
            organization=self.org,
            customer=self.customer,
            title="Web Hosting & Care",
            start_date=datetime.date.today(),
            billing_cycle=BillingCycle.MONTHLY,
            auto_generate=True,
            items_data=[
                {"description": "Server Hosting", "qty": Decimal("1"), "unit_price": Decimal("50000.00")},
                {"description": "SSL Certificate", "qty": Decimal("1"), "unit_price": Decimal("10000.00")}
            ],
            template=self.template,
            user=self.user
        )

        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(sub.total_amount, Decimal("60000.00"))
        self.assertEqual(sub.mrr, Decimal("60000.00"))
        self.assertEqual(sub.arr, Decimal("720000.00"))

    def test_recurring_invoice_generation_and_command(self):
        sub = SubscriptionService.create_subscription(
            organization=self.org,
            customer=self.customer,
            title="Recurring Support",
            start_date=datetime.date.today() - datetime.timedelta(days=1),
            billing_cycle=BillingCycle.MONTHLY,
            auto_generate=True,
            items_data=[
                {"description": "ICT Maintenance", "qty": Decimal("1"), "unit_price": Decimal("100000.00")}
            ],
            user=self.user
        )

        # Execute management command
        call_command("generate_recurring_invoices")

        sub.refresh_from_db()
        self.assertGreater(sub.next_invoice_date, datetime.date.today())
        # Check generated invoice exists
        self.assertEqual(sub.customer.invoice_set.count(), 1)
        inv = sub.customer.invoice_set.first()
        self.assertEqual(inv.total_due, Decimal("100000.00"))

    def test_subscription_pause_resume_cancel(self):
        sub = SubscriptionService.create_subscription(
            organization=self.org,
            customer=self.customer,
            title="Cloud Hosting",
            start_date=datetime.date.today(),
            billing_cycle=BillingCycle.MONTHLY,
            user=self.user
        )

        SubscriptionService.pause(sub, user=self.user)
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatus.PAUSED)
        self.assertEqual(sub.mrr, Decimal("0.00"))

        SubscriptionService.resume(sub, user=self.user)
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)

        SubscriptionService.cancel(sub, user=self.user)
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)

