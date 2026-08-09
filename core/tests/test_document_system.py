from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse

from invoices.models import Organization, Product, ProductCategory, Customer, Invoice, Quotation, QuotationItem, Receipt, Payment, UserProfile
from inventory.models import Warehouse, GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
from core.documents.context_builder import DocumentContextBuilder
from sales.services.quotation_service import QuotationService

User = get_user_model()


class DocumentSystemTestCase(TestCase):

    def setUp(self):
        # Org A
        self.org_a = Organization.objects.create(
            name="ArewaNet ERP Solutions",
            slug="arewanet-erp-solutions",
            phone="08020000000",
            email="info@arewanet.ng",
            address="Kano, Nigeria"
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
        self.org_b = Organization.objects.create(name="Sahara Retail B", slug="sahara-retail-b")
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
        ctx_inv = DocumentContextBuilder.build(inv, extra_context={"customer": inv.customer, "doc_type": "INVOICE"})
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
        ctx_rcpt = DocumentContextBuilder.build(rcpt, extra_context={"customer": inv.customer, "doc_type": "PAYMENT RECEIPT"})
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

    def test_quotation_pdf_endpoint(self):
        self.client.login(username="docuser_a", password="password123")
        qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_date=date.today(),
            subtotal=Decimal("150000.00"),
            total=Decimal("150000.00")
        )
        url = reverse('quotation_pdf', kwargs={'pk': qtn.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_quotation_tenant_isolation(self):
        qtn_a = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            subtotal=Decimal("50000.00"),
            total=Decimal("50000.00")
        )
        # User B cannot access User A's quotation
        self.client.login(username="docuser_b", password="password123")
        url = reverse('quotation_detail', kwargs={'pk': qtn_a.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_quotation_large_item_set_and_zero_discount_edge_cases(self):
        qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            subtotal=Decimal("300000.00"),
            discount=Decimal("0.00"),
            vat=Decimal("0.00"),
            total=Decimal("300000.00")
        )
        for i in range(1, 35):
            QuotationItem.objects.create(
                quotation=qtn,
                description=f"Hardware Component Model #{i} - Extended Spec Description",
                qty=Decimal("1.00"),
                unit_price=Decimal("10000.00"),
                total=Decimal("10000.00")
            )
        ctx = DocumentContextBuilder.build(qtn, extra_context={"customer": qtn.customer, "doc_type": "QUOTATION"})
        html = render_to_string("documents/quotation/detail.html", ctx)

        self.assertIn("Hardware Component Model #34", html)
        # Zero discount and tax rows should not appear
        self.assertNotIn("Discount:", html)
        self.assertNotIn("Tax / VAT:", html)
