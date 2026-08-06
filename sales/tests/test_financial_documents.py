import io
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from invoices.models import Organization, Customer, Invoice, InvoiceItem
from sales.models import CreditNote, DebitNote
from sales.services import CreditNoteService, DebitNoteService, StatementService, AgingService
from core.choices import CreditNoteStatus, DebitNoteStatus
from core.documents.pdf_service import PDFService

User = get_user_model()


class FinancialDocumentsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password")
        self.org = Organization.objects.create(name="ArewaNet Test Org", slug="arewanet-test-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Acme Limited",
            email="info@acme.com",
            phone="08012345678"
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-0001",
            invoice_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            project_name="ERP Setup",
            deployment_phase="Phase 1",
            subtotal=Decimal("100000.00"),
            vat=Decimal("0.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            description="Software License",
            qty=Decimal("1.00"),
            unit_price=Decimal("100000.00"),
            total=Decimal("100000.00")
        )

    def test_credit_note_workflow(self):
        # 1. Issue Credit Note of N20,000
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

        # 2. Cancel Credit Note
        CreditNoteService.cancel_credit_note(cn, user=self.user)
        cn.refresh_from_db()
        self.assertEqual(cn.status, CreditNoteStatus.CANCELLED)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_credit_notes, Decimal("0.00"))
        self.assertEqual(self.invoice.effective_total_due, Decimal("100000.00"))

    def test_debit_note_workflow(self):
        # Issue Debit Note of N15,000
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
        # Due date was 10 days ago (<= 30 days overdue) -> 'current'
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
