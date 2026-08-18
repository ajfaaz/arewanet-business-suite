from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from invoices.models import Organization, Customer, Quotation, QuotationItem, QuotationTemplate, UserProfile, ActivityLog
from invoices.services.quotation_pdf_service import QuotationPDFService
from core.documents.pdf_service import PDFService


class QuotationPDFPart7TestCase(TestCase):

    def setUp(self):
        self.user_a = User.objects.create_superuser(username="admin_part7_a", password="password123", email="admin_part7_a@example.com")
        self.user_b = User.objects.create_superuser(username="admin_part7_b", password="password123", email="admin_part7_b@example.com")

        self.org_a = Organization.objects.create(
            name="Alpha Enterprises",
            slug="alpha-ent",
            currency="NGN",
            default_vat=Decimal("7.50"),
            phone="09011111111",
            email="info@alpha.com"
        )
        UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        self.org_b = Organization.objects.create(
            name="Beta Logistics",
            slug="beta-log",
            currency="USD"
        )
        UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Apex Global Ltd",
            email="contact@apex.com"
        )

        self.customer_b = Customer.objects.create(
            organization=self.org_b,
            company_name="Beta Client",
            email="client@beta.com"
        )

        # Templates for Org A
        self.tpl_modern_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Modern",
            style="modern",
            is_active=True,
            is_default=True
        )

        self.tpl_classic_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Classic",
            style="classic",
            is_active=True,
            is_default=False
        )

        self.tpl_minimal_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Minimal",
            style="minimal",
            is_active=True,
            is_default=False
        )

        # Quotation for Org A
        self.qtn_a = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QTN-2026-0007",
            quotation_date=date.today(),
            subtotal=Decimal("150000.00"),
            total=Decimal("161250.00"),
            status="DRAFT",
            template=self.tpl_modern_a
        )

        QuotationItem.objects.create(
            quotation=self.qtn_a,
            description="Enterprise Network Upgrade Phase 1",
            qty=Decimal("1.00"),
            unit_price=Decimal("150000.00"),
            total=Decimal("150000.00")
        )

        # Quotation for Org B
        self.qtn_b = Quotation.objects.create(
            organization=self.org_b,
            customer=self.customer_b,
            quotation_no="QTN-BETA-0001",
            quotation_date=date.today(),
            subtotal=Decimal("5000.00"),
            total=Decimal("5000.00"),
            status="DRAFT"
        )

    def test_quotation_pdf_returns_200_and_pdf_header(self):
        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(res.content.startswith(b'%PDF'))

    def test_pdf_filename_matches_quotation_number(self):
        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        res = self.client.get(url)

        self.assertIn("Content-Disposition", res)
        self.assertIn("Quotation-QTN-2026-0007.pdf", res["Content-Disposition"])

    def test_tenant_isolation_rejects_cross_org_pdf(self):
        # User A attempts to download Org B's quotation PDF
        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_b.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 404)

    def test_unauthenticated_user_redirected_to_login(self):
        self.client.logout()
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_historical_template_stability_in_pdf(self):
        # Assign Classic to qtn_a
        self.qtn_a.template = self.tpl_classic_a
        self.qtn_a.save()

        # Change Org A default template to Minimal
        self.tpl_minimal_a.is_default = True
        self.tpl_minimal_a.save()

        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b'%PDF'))
        # Saved template MUST remain Classic
        self.qtn_a.refresh_from_db()
        self.assertEqual(self.qtn_a.template, self.tpl_classic_a)

    def test_pdf_generation_when_template_deactivated(self):
        # Deactivate qtn_a's template
        self.tpl_classic_a.is_active = False
        self.tpl_classic_a.save()
        self.qtn_a.template = self.tpl_classic_a
        self.qtn_a.save()

        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b'%PDF'))

    def test_pdf_generation_missing_logo(self):
        # Ensure org_a logo is None
        self.org_a.logo = None
        self.org_a.save()

        pdf_bytes = QuotationPDFService.generate(self.qtn_a)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_multi_page_items_rendering(self):
        # Create a quotation with 30 items
        multi_qtn = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QTN-MULTIPAGE-001",
            quotation_date=date.today(),
            template=self.tpl_classic_a
        )
        for i in range(1, 31):
            QuotationItem.objects.create(
                quotation=multi_qtn,
                description=f"Hardware Component Module Unit Model Line Item #{i}",
                qty=Decimal("1.00"),
                unit_price=Decimal("12500.00"),
                total=Decimal("12500.00")
            )

        pdf_bytes = QuotationPDFService.generate(multi_qtn)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_preview_override_pdf(self):
        # Override to Minimal template via query param
        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk}) + f"?template_id={self.tpl_minimal_a.pk}"
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b'%PDF'))
        # DB template must remain Modern
        self.qtn_a.refresh_from_db()
        self.assertEqual(self.qtn_a.template, self.tpl_modern_a)

    def test_pdf_audit_log(self):
        self.client.login(username="admin_part7_a", password="password123")
        url = reverse('quotation_pdf', kwargs={'pk': self.qtn_a.pk})
        self.client.get(url)

        self.assertTrue(
            ActivityLog.objects.filter(
                user=self.user_a,
                action__icontains="Generated PDF for Quotation QTN-2026-0007"
            ).exists()
        )

    def test_quotation_pdf_service_interface(self):
        pdf_bytes = QuotationPDFService.generate(self.qtn_a)
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

        pdf_bytes_facade = PDFService.generate_quotation(self.qtn_a)
        self.assertTrue(pdf_bytes_facade.startswith(b'%PDF'))
