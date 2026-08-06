from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.choices import PaymentMethod, PaymentStatus, InvoiceStatus
from invoices.models import Organization, Customer, Invoice
from sales.payments.models import Payment, PaymentAllocation
from sales.payments.services import PaymentService
from sales.payments.selectors import PaymentSelectors

User = get_user_model()


class EnterprisePaymentCenterTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="paymentadmin", password="password123")
        self.org = Organization.objects.create(name="Enterprise Tech Ltd", slug="enterprise-tech")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Kano Traders Corp",
            email="kano@traders.com"
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-0001",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            project_name="Server Infrastructure Deployment",
            deployment_phase="Phase 1",
            subtotal=Decimal("500000.00"),
            total_due=Decimal("500000.00"),
            status=InvoiceStatus.UNPAID
        )

    def test_single_invoice_partial_and_full_payment(self):
        # 1. Record Partial Payment ₦100,000
        p1 = PaymentService.receive_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("100000.00"),
            payment_method=PaymentMethod.CASH,
            invoice=self.invoice,
            notes="First Partial Payment",
            user=self.user
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_paid, Decimal("100000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("400000.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIAL)

        # 2. Record Second Partial Payment ₦200,000 via Transfer
        p2 = PaymentService.receive_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("200000.00"),
            payment_method=PaymentMethod.BANK,
            invoice=self.invoice,
            notes="Second Payment",
            user=self.user
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_paid, Decimal("300000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("200000.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIAL)

        # 3. Final Settlement ₦200,000 via POS
        p3 = PaymentService.receive_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("200000.00"),
            payment_method=PaymentMethod.POS,
            invoice=self.invoice,
            notes="Final Settlement",
            user=self.user
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_paid, Decimal("500000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("0.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

    def test_payment_reversal_and_refund(self):
        p = PaymentService.receive_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.BANK,
            invoice=self.invoice,
            user=self.user
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

        # Reverse Payment
        PaymentService.reverse_payment(p, reason="Bounced Transfer", user=self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(p.status, PaymentStatus.REVERSED)
        self.assertEqual(self.invoice.total_paid, Decimal("0.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("500000.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.UNPAID)

    def test_multi_invoice_payment_allocation(self):
        inv2 = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-0002",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=15),
            project_name="ERP Software Upgrade",
            deployment_phase="Phase 2",
            subtotal=Decimal("300000.00"),
            total_due=Decimal("300000.00"),
            status=InvoiceStatus.UNPAID
        )

        # Total outstanding = ₦500,000 + ₦300,000 = ₦800,000
        # Customer pays lump-sum ₦600,000
        bulk_payment = PaymentService.allocate_multi_invoice_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("600000.00"),
            payment_method=PaymentMethod.BANK,
            reference="BULK-TRF-00192",
            user=self.user
        )

        self.assertEqual(bulk_payment.amount, Decimal("600000.00"))
        self.assertEqual(bulk_payment.allocations.count(), 2)

        inv2.refresh_from_db()
        self.invoice.refresh_from_db()

        # Inv2 due date was earlier (+15 days vs +30 days), so Inv2 is fully settled first (₦300,000)
        self.assertEqual(inv2.total_paid, Decimal("300000.00"))
        self.assertEqual(inv2.status, InvoiceStatus.PAID)

        # Remaining ₦300,000 allocated to self.invoice (₦500,000 - ₦300,000 = ₦200,000 remaining)
        self.assertEqual(self.invoice.total_paid, Decimal("300000.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("200000.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIAL)

    def test_payment_selectors_and_dashboard_stats(self):
        PaymentService.receive_payment(
            organization=self.org,
            customer=self.customer,
            amount=Decimal("150000.00"),
            payment_method=PaymentMethod.CASH,
            invoice=self.invoice,
            user=self.user
        )

        stats = PaymentSelectors.get_payment_center_stats(self.org)
        self.assertEqual(stats['todays_collections'], Decimal("150000.00"))
        self.assertEqual(stats['monthly_collections'], Decimal("150000.00"))

        timeline = PaymentSelectors.get_payments_for_timeline(self.invoice)
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]['amount'], Decimal("150000.00"))
