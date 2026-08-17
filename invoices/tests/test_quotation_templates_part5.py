from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from invoices.models import (
    Organization, Customer, Product, Quotation, QuotationItem, QuotationTemplate, UserProfile
)
from invoices.services.quotation_template_service import QuotationTemplateService
from invoices.services.template_renderer import QuotationTemplateRenderer


class QuotationTemplatesPart5TestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='tpluser5', password='password123', email='admin@example.com')
        self.client.login(username='tpluser5', password='password123')

        self.org_a = Organization.objects.create(
            name="Alpha Enterprises",
            slug="alpha-enterprises",
            phone="+234 800 111 2222",
            email="info@alpha.example.com",
            address="10 Alpha Way, Abuja",
            bank_name="First Bank of Nigeria",
            account_name="Alpha Enterprises",
            account_number="0123456789",
            terms="Standard 14-day payment policy applies."
        )
        UserProfile.objects.create(user=self.user, organization=self.org_a, role='ADMIN')

        self.org_b = Organization.objects.create(
            name="Beta Solutions",
            slug="beta-solutions"
        )

        self.customer = Customer.objects.create(
            organization=self.org_a,
            company_name="ABC Technologies Ltd",
            contact_person="Jane Doe",
            email="jane@abctech.example.com",
            phone="+234 803 999 8888",
            address="45 Commercial Road, Ikeja, Lagos"
        )

        self.service_a = QuotationTemplateService(organization=self.org_a)
        self.modern_tpl = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Modern",
            style="modern",
            is_active=True,
            is_default=True
        )
        self.classic_tpl = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Classic",
            style="classic",
            is_active=True,
            is_default=False
        )
        self.minimal_tpl = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Minimal",
            style="minimal",
            is_active=True,
            is_default=False
        )

        self.quotation = Quotation.objects.create(
            organization=self.org_a,
            quotation_no="QT-00023",
            customer=self.customer,
            quotation_date=date(2026, 8, 16),
            valid_until=date(2026, 8, 30),
            subtotal=Decimal("600000.00"),
            discount=Decimal("20000.00"),
            vat=Decimal("7.50"),
            total=Decimal("580000.00"),
            notes="Please review and confirm scope.",
            terms="1. 50% deposit required on approval.\n2. Prices valid for 14 days."
        )

        QuotationItem.objects.create(
            quotation=self.quotation,
            description="Website Development & Custom Portal",
            qty=Decimal("1.00"),
            unit_price=Decimal("500000.00"),
            total=Decimal("500000.00")
        )
        QuotationItem.objects.create(
            quotation=self.quotation,
            description="Cloud Hosting & SSL Configuration",
            qty=Decimal("1.00"),
            unit_price=Decimal("100000.00"),
            total=Decimal("100000.00")
        )

    def test_modern_style_resolves(self):
        url = reverse('quotation_template_preview', kwargs={'pk': self.modern_tpl.pk}) + f"?quotation={self.quotation.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "modern-doc")
        self.assertContains(res, "QT-00023")
        self.assertContains(res, "ABC Technologies Ltd")

    def test_classic_style_resolves(self):
        url = reverse('quotation_template_preview', kwargs={'pk': self.classic_tpl.pk}) + f"?quotation={self.quotation.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "classic-doc")
        self.assertContains(res, "QUOTATION")
        self.assertContains(res, "Customer Information")

    def test_minimal_style_resolves(self):
        url = reverse('quotation_template_preview', kwargs={'pk': self.minimal_tpl.pk}) + f"?quotation={self.quotation.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "minimal-doc")
        self.assertContains(res, "QUOTATION")
        self.assertContains(res, "minimal-grand-total")

    def test_unknown_style_handled_safely(self):
        unknown_tpl = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Unknown Custom Style",
            style="non_existent_style_xyz",
            is_active=True
        )
        url = reverse('quotation_template_preview', kwargs={'pk': unknown_tpl.pk}) + f"?quotation={self.quotation.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "modern-doc")

    def test_same_quotation_data_rendered_identically_across_styles(self):
        renderer = QuotationTemplateRenderer(organization=self.org_a)

        modern_html = renderer.render(self.quotation, template=self.modern_tpl)
        classic_html = renderer.render(self.quotation, template=self.classic_tpl)
        minimal_html = renderer.render(self.quotation, template=self.minimal_tpl)

        for html in [modern_html, classic_html, minimal_html]:
            self.assertIn("QT-00023", html)
            self.assertIn("ABC Technologies Ltd", html)
            self.assertIn("Website Development", html)
            self.assertIn("Cloud Hosting", html)
            self.assertIn("580000.00", html)
            self.assertIn("600000.00", html)

    def test_organization_isolation(self):
        beta_tpl = QuotationTemplate.objects.create(
            organization=self.org_b,
            name="Beta Template",
            style="modern"
        )
        url = reverse('quotation_template_preview', kwargs={'pk': beta_tpl.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_inactive_template_protection(self):
        inactive_tpl = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Inactive Classic",
            style="classic",
            is_active=False
        )
        with self.assertRaises(ValueError):
            self.service_a.set_default_template(inactive_tpl.id)

    def test_missing_logo_and_optional_fields_handled(self):
        bare_org = Organization.objects.create(name="Bare Minimum Org", slug="bare-min-org")
        bare_customer = Customer.objects.create(organization=bare_org, company_name="Basic Customer")
        bare_qtn = Quotation.objects.create(
            organization=bare_org,
            quotation_no="QT-BARE-01",
            customer=bare_customer,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00")
        )

        renderer = QuotationTemplateRenderer(organization=bare_org)
        for style in ['modern', 'classic', 'minimal']:
            tpl = QuotationTemplate(organization=bare_org, name="Test", style=style)
            html = renderer.render(bare_qtn, template=tpl)
            self.assertIn("Bare Minimum Org", html)
            self.assertIn("QT-BARE-01", html)

    def test_large_quotation_item_list(self):
        large_qtn = Quotation.objects.create(
            organization=self.org_a,
            quotation_no="QT-LARGE-01",
            customer=self.customer,
            subtotal=Decimal("500000.00"),
            total=Decimal("500000.00")
        )
        for i in range(1, 55):
            QuotationItem.objects.create(
                quotation=large_qtn,
                description=f"Enterprise Infrastructure Component Line Item #{i} with detailed tech specs",
                qty=Decimal("1.00"),
                unit_price=Decimal("1000.00"),
                total=Decimal("1000.00")
            )

        renderer = QuotationTemplateRenderer(organization=self.org_a)
        for tpl in [self.modern_tpl, self.classic_tpl, self.minimal_tpl]:
            html = renderer.render(large_qtn, template=tpl)
            self.assertIn("QT-LARGE-01", html)
            self.assertIn("Component Line Item #54", html)
