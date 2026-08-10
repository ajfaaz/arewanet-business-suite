from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse

from invoices.models import Organization, Product, ProductCategory, Customer, Invoice, InvoiceItem, Quotation, QuotationItem, Receipt, Payment, UserProfile
from inventory.models import Warehouse, GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
from core.documents.context_builder import DocumentContextBuilder
from sales.services.quotation_service import QuotationService
from invoices.views import _build_receipt_context

User = get_user_model()


class DocumentSystemTestCase(TestCase):

    def setUp(self):
        # Org A
        self.org_a = Organization.objects.create(
            name="ArewaNet ERP Solutions",
            slug="arewanet-erp-solutions",
            phone="08020000000",
            email="info@arewanet.ng",
            address="Kano, Nigeria",
            bank_name="FCMB",
            account_name="ArewaNet ERP Solutions",
            account_number="1032574456"
        )
        self.user_a = User.objects.create_user(username="docuser_a", password="password123")
        UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Northern Tech Innovations Ltd",
            email="contact@northerntech.ng",
            phone="08030000000"
        )
        self.cat_a = ProductCategory.objects.create(organization=self.org_a, name="Software & Systems")
        self.product_a = Product.objects.create(
            organization=self.org_a,
            category=self.cat_a,
            name="ERP Enterprise License",
            sku="ERP-ENT",
            selling_price=Decimal("250000.00"),
            cost_price=Decimal("180000.00")
        )
        self.wh_a = Warehouse.objects.create(organization=self.org_a, name="Central Warehouse", code="WH-CENTRAL")

        # Org B (Tenant isolation)
        self.org_b = Organization.objects.create(
            name="Sahara Retail B",
            slug="sahara-retail-b",
            bank_name="Zenith Bank",
            account_name="Sahara Retail B",
            account_number="2006219801"
        )
        self.user_b = User.objects.create_user(username="docuser_b", password="password123")
        UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")

    def test_document_context_builder_status_badges(self):
        qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_date=date.today(),
            subtotal=Decimal("500000.00"),
            total=Decimal("500000.00"),
            status="DRAFT"
        )
        ctx = DocumentContextBuilder.build(qtn)
        self.assertEqual(ctx["status_badge_class"], "badge-warning")
        self.assertEqual(ctx["organization"], self.org_a)
        self.assertTrue("Document QTN-" in ctx["title"])

    def test_quotation_conversion_to_invoice(self):
        qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_date=date.today(),
            subtotal=Decimal("500000.00"),
            vat=Decimal("37500.00"),
            total=Decimal("537500.00"),
            status="DRAFT"
        )
        QuotationItem.objects.create(
            quotation=qtn,
            product=self.product_a,
            description="2x Enterprise Licenses",
            qty=Decimal("2.00"),
            unit_price=Decimal("250000.00"),
            total=Decimal("500000.00")
        )

        invoice = QuotationService.convert_to_invoice(qtn, user=self.user_a)

        qtn.refresh_from_db()
        self.assertEqual(qtn.status, "CONVERTED")
        self.assertEqual(invoice.customer, self.customer_a)
        self.assertEqual(invoice.total, Decimal("537500.00"))
        self.assertEqual(invoice.items.count(), 1)

    def test_unified_document_template_rendering(self):
        # 1. Quotation Template
        qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_date=date.today(),
            subtotal=Decimal("250000.00"),
            total=Decimal("250000.00")
        )
        QuotationItem.objects.create(
            quotation=qtn,
            product=self.product_a,
            description="Single License",
            qty=Decimal("1.00"),
            unit_price=Decimal("250000.00"),
            total=Decimal("250000.00")
        )
        ctx_qtn = DocumentContextBuilder.build(qtn, extra_context={"customer": qtn.customer, "doc_type": "QUOTATION"})
        html_qtn = render_to_string("documents/quotation/detail.html", ctx_qtn)
        self.assertIn("ArewaNet ERP Solutions", html_qtn)
        self.assertIn("Northern Tech Innovations Ltd", html_qtn)
        self.assertIn("QUOTATION", html_qtn)

        # 2. Invoice Template
        inv = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal("250000.00"),
            total_due=Decimal("250000.00")
        )
        ctx_inv = DocumentContextBuilder.build(inv, extra_context={"invoice": inv, "customer": inv.customer, "doc_type": "INVOICE"})
        html_inv = render_to_string("documents/invoice/detail.html", ctx_inv)
        self.assertIn("INVOICE", html_inv)

        # 3. Receipt Template
        pmt = Payment.objects.create(
            organization=self.org_a,
            invoice=inv,
            amount=Decimal("250000.00"),
            payment_date=date.today(),
            reference="TRX-1001"
        )
        rcpt = getattr(pmt, 'receipt', None) or Receipt.objects.filter(payment=pmt).first()
        if not rcpt:
            rcpt = Receipt.objects.create(organization=self.org_a, payment=pmt, receipt_no="REC-1001")
        ctx_rcpt = _build_receipt_context(rcpt)
        html_rcpt = render_to_string("documents/receipt/detail.html", ctx_rcpt)
        self.assertIn("PAYMENT RECEIPT", html_rcpt)
        self.assertIn("TRX-1001", html_rcpt)

        # 4. GRN Template
        grn = GoodsReceivedNote.objects.create(
            organization=self.org_a,
            document_number="GRN-2026-000001",
            warehouse=self.wh_a,
            supplier_name="Tech Distributors Nigeria",
            received_date=date.today()
        )
        ctx_grn = DocumentContextBuilder.build(grn, extra_context={"warehouse": self.wh_a, "doc_type": "GOODS RECEIVED NOTE"})
        html_grn = render_to_string("documents/grn/detail.html", ctx_grn)
        self.assertIn("GOODS RECEIVED NOTE", html_grn)
        self.assertIn("Tech Distributors Nigeria", html_grn)

    def test_invoice_payment_scenarios_and_rendering(self):
        # 1. Unpaid Invoice
        inv_unpaid = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )
        self.assertEqual(inv_unpaid.total_paid, Decimal("0.00"))
        self.assertEqual(inv_unpaid.balance, Decimal("100000.00"))

        ctx_unpaid = DocumentContextBuilder.build(inv_unpaid, extra_context={"invoice": inv_unpaid, "customer": inv_unpaid.customer, "doc_type": "INVOICE"})
        html_unpaid = render_to_string("documents/invoice/detail.html", ctx_unpaid)
        self.assertIn("₦100,000.00", html_unpaid)

        # 2. Partially Paid Invoice
        inv_partial = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="PARTIAL"
        )
        Payment.objects.create(
            organization=self.org_a,
            invoice=inv_partial,
            amount=Decimal("40000.00"),
            payment_date=date.today(),
            reference="TRX-PART-1"
        )
        self.assertEqual(inv_partial.total_paid, Decimal("40000.00"))
        self.assertEqual(inv_partial.balance, Decimal("60000.00"))

        ctx_partial = DocumentContextBuilder.build(inv_partial, extra_context={"invoice": inv_partial, "customer": inv_partial.customer, "doc_type": "INVOICE"})
        html_partial = render_to_string("documents/invoice/detail.html", ctx_partial)
        self.assertIn("₦40,000.00", html_partial)
        self.assertIn("₦60,000.00", html_partial)

        # 3. Fully Paid Invoice
        inv_paid = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="PAID"
        )
        Payment.objects.create(
            organization=self.org_a,
            invoice=inv_paid,
            amount=Decimal("100000.00"),
            payment_date=date.today(),
            reference="TRX-FULL-1"
        )
        self.assertEqual(inv_paid.total_paid, Decimal("100000.00"))
        self.assertEqual(inv_paid.balance, Decimal("0.00"))

        ctx_paid = DocumentContextBuilder.build(inv_paid, extra_context={"invoice": inv_paid, "customer": inv_paid.customer, "doc_type": "INVOICE"})
        html_paid = render_to_string("documents/invoice/detail.html", ctx_paid)
        self.assertIn("PAID", html_paid)
        self.assertIn("₦0.00", html_paid)

    def test_invoice_pdf_endpoint(self):
        self.client.login(username="docuser_a", password="password123")
        inv = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("150000.00"),
            total_due=Decimal("150000.00")
        )
        url = reverse('invoice_pdf', kwargs={'pk': inv.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_invoice_tenant_isolation_and_branding(self):
        inv_a = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("50000.00"),
            total_due=Decimal("50000.00")
        )
        # User B cannot access User A's invoice
        self.client.login(username="docuser_b", password="password123")
        url = reverse('invoice_detail', kwargs={'pk': inv_a.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

        # Organization B Invoice Branding Test
        cust_b = Customer.objects.create(organization=self.org_b, company_name="Sahara Client Ltd")
        inv_b = Invoice.objects.create(
            organization=self.org_b,
            customer=cust_b,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("75000.00"),
            total_due=Decimal("75000.00")
        )
        ctx_b = DocumentContextBuilder.build(inv_b, extra_context={"invoice": inv_b, "customer": cust_b})
        html_b = render_to_string("documents/invoice/detail.html", ctx_b)

        self.assertIn("Sahara Retail B", html_b)
        self.assertIn("Zenith Bank", html_b)
        self.assertNotIn("ArewaNet ERP Solutions", html_b)
        self.assertNotIn("FCMB", html_b)

    def test_long_invoice_rendering(self):
        inv = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("350000.00"),
            total_due=Decimal("350000.00")
        )
        for i in range(1, 35):
            InvoiceItem.objects.create(
                invoice=inv,
                description=f"Long Line Item description text for item #{i} with details",
                qty=Decimal("1.00"),
                unit_price=Decimal("10000.00"),
                total=Decimal("10000.00")
            )
        ctx = DocumentContextBuilder.build(inv, extra_context={"invoice": inv, "customer": inv.customer, "doc_type": "INVOICE"})
        html = render_to_string("documents/invoice/detail.html", ctx)
        self.assertIn("Long Line Item description text for item #34", html)

    def test_receipt_multiple_payments_history_breakdown(self):
        inv = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("1000000.00"),
            total_due=Decimal("1000000.00")
        )

        # Payment 1: 300k
        p1 = Payment.objects.create(
            organization=self.org_a,
            invoice=inv,
            amount=Decimal("300000.00"),
            payment_date=date.today(),
            reference="TRX-MULT-1"
        )
        r1 = getattr(p1, 'receipt', None) or Receipt.objects.filter(payment=p1).first()
        if not r1:
            r1 = Receipt.objects.create(organization=self.org_a, payment=p1, receipt_no="RCPT-MULT-1")

        ctx1 = _build_receipt_context(r1)
        self.assertEqual(ctx1["previously_paid"], Decimal("0.00"))
        self.assertEqual(ctx1["balance_remaining"], Decimal("700000.00"))

        # Payment 2: 400k
        p2 = Payment.objects.create(
            organization=self.org_a,
            invoice=inv,
            amount=Decimal("400000.00"),
            payment_date=date.today(),
            reference="TRX-MULT-2"
        )
        r2 = getattr(p2, 'receipt', None) or Receipt.objects.filter(payment=p2).first()
        if not r2:
            r2 = Receipt.objects.create(organization=self.org_a, payment=p2, receipt_no="RCPT-MULT-2")

        ctx2 = _build_receipt_context(r2)
        self.assertEqual(ctx2["previously_paid"], Decimal("300000.00"))
        self.assertEqual(ctx2["balance_remaining"], Decimal("300000.00"))

        # Payment 3: 300k (Fully Paid)
        p3 = Payment.objects.create(
            organization=self.org_a,
            invoice=inv,
            amount=Decimal("300000.00"),
            payment_date=date.today(),
            reference="TRX-MULT-3"
        )
        inv.status = "PAID"
        inv.save()
        r3 = getattr(p3, 'receipt', None) or Receipt.objects.filter(payment=p3).first()
        if not r3:
            r3 = Receipt.objects.create(organization=self.org_a, payment=p3, receipt_no="RCPT-MULT-3")

        ctx3 = _build_receipt_context(r3)
        self.assertEqual(ctx3["previously_paid"], Decimal("700000.00"))
        self.assertEqual(ctx3["balance_remaining"], Decimal("0.00"))

        html3 = render_to_string("documents/receipt/detail.html", ctx3)
        self.assertIn("FULLY PAID", html3)
        self.assertIn(r3.receipt_no, html3)

    def test_receipt_pdf_endpoint(self):
        self.client.login(username="docuser_a", password="password123")
        inv = Invoice.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("150000.00"),
            total_due=Decimal("150000.00")
        )
        pmt = Payment.objects.create(
            organization=self.org_a,
            invoice=inv,
            amount=Decimal("150000.00"),
            payment_date=date.today(),
            reference="TRX-PDF-1"
        )
        rcpt = getattr(pmt, 'receipt', None) or Receipt.objects.filter(payment=pmt).first()
        if not rcpt:
            rcpt = Receipt.objects.create(organization=self.org_a, payment=pmt, receipt_no="RCPT-PDF-1")

        url = reverse('receipt_pdf', kwargs={'pk': rcpt.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(f"receipt-{rcpt.receipt_no}.pdf", res['Content-Disposition'])
