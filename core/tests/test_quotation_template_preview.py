from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, Customer, Quotation, QuotationItem, QuotationTemplate

User = get_user_model()


class QuotationTemplatePreviewTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(name="Preview Org A", slug="preview-org-a")
        self.org_b = Organization.objects.create(name="Preview Org B", slug="preview-org-b")

        self.role_admin = Role.objects.get(slug="administrator")

        # Create permissions
        self.perm_tpl_view, _ = Permission.objects.get_or_create(code="quotation_template.view", defaults={"name": "View Template", "module": "quotation_template", "action": "view"})
        self.perm_quote_view, _ = Permission.objects.get_or_create(code="quotation.view", defaults={"name": "View Quotation", "module": "quotation", "action": "view"})

        # Admin user for Org A
        self.user_admin_a = User.objects.create_user(username="prev_admin_a", password="password123")
        self.m_admin_a = OrganizationMembership.objects.create(user=self.user_admin_a, organization=self.org_a, role=self.role_admin)

        # Sales user for Org A (has quotation.view but NOT quotation_template.view)
        self.role_sales = Role.objects.create(name="Sales Officer Custom", slug="sales-officer-custom", is_active=True)
        self.role_sales.permissions.add(self.perm_quote_view)
        self.user_sales_a = User.objects.create_user(username="prev_sales_a", password="password123")
        self.m_sales_a = OrganizationMembership.objects.create(user=self.user_sales_a, organization=self.org_a, role=self.role_sales)

        # Unauthorized user (no view perms)
        self.role_unauth = Role.objects.create(name="No Perm Role", slug="no-perm-role", is_active=True)
        self.user_unauth = User.objects.create_user(username="prev_unauth", password="password123")
        self.m_unauth = OrganizationMembership.objects.create(user=self.user_unauth, organization=self.org_a, role=self.role_unauth)

        # Customers & Real Quotations
        self.cust_a = Customer.objects.create(organization=self.org_a, company_name="Org A Client Ltd", email="clienta@example.com")
        self.quote_a = Quotation.objects.create(
            organization=self.org_a,
            customer=self.cust_a,
            quotation_date=date.today(),
            subtotal=Decimal("150000.00"),
            total=Decimal("161250.00"),
            vat=Decimal("7.50"),
            notes="Real quote notes"
        )
        QuotationItem.objects.create(quotation=self.quote_a, description="Real Server Item", qty=1, unit_price=Decimal("150000.00"), total=Decimal("150000.00"))

        self.cust_b = Customer.objects.create(organization=self.org_b, company_name="Org B Client Ltd", email="clientb@example.com")
        self.quote_b = Quotation.objects.create(
            organization=self.org_b,
            customer=self.cust_b,
            quotation_date=date.today(),
            subtotal=Decimal("500000.00"),
            total=Decimal("500000.00")
        )

        # Templates
        self.tpl_modern_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Modern Template A",
            style="modern",
            is_active=True,
            is_default=True
        )
        self.tpl_classic_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Classic Template A",
            style="classic",
            is_active=True
        )
        self.tpl_minimal_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Minimal Template A",
            style="minimal",
            is_active=True
        )

        self.tpl_b = QuotationTemplate.objects.create(
            organization=self.org_b,
            name="Template Org B",
            style="modern",
            is_active=True
        )

    def test_preview_demo_data_without_quotation_id(self):
        self.client.login(username="prev_admin_a", password="password123")
        url = reverse("quotation_template_preview", kwargs={"pk": self.tpl_modern_a.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "quotations/preview/modern.html")
        self.assertContains(response, "Demo Customer Ltd")
        self.assertContains(response, "QT-DEMO-0001")
        self.assertContains(response, "Professional Software Development")

        # Verify no fake database quotation was created
        self.assertEqual(Quotation.objects.filter(organization=self.org_a).count(), 1)

    def test_preview_with_real_quotation(self):
        self.client.login(username="prev_admin_a", password="password123")
        url = f"{reverse('quotation_template_preview', kwargs={'pk': self.tpl_modern_a.pk})}?quotation={self.quote_a.pk}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Org A Client Ltd")
        self.assertContains(response, self.quote_a.quotation_no)
        self.assertContains(response, "Real Server Item")

    def test_preview_cross_tenant_quotation_denied(self):
        self.client.login(username="prev_admin_a", password="password123")
        # Attempting Org A template + Org B quotation -> 404
        url = f"{reverse('quotation_template_preview', kwargs={'pk': self.tpl_modern_a.pk})}?quotation={self.quote_b.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_preview_cross_tenant_template_denied(self):
        self.client.login(username="prev_admin_a", password="password123")
        # Attempting Org A user + Org B template -> 404
        url = reverse("quotation_template_preview", kwargs={"pk": self.tpl_b.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_preview_style_rendering(self):
        self.client.login(username="prev_admin_a", password="password123")

        # Modern
        res_mod = self.client.get(reverse("quotation_template_preview", kwargs={"pk": self.tpl_modern_a.pk}))
        self.assertTemplateUsed(res_mod, "quotations/preview/modern.html")

        # Classic
        res_clas = self.client.get(reverse("quotation_template_preview", kwargs={"pk": self.tpl_classic_a.pk}))
        self.assertTemplateUsed(res_clas, "quotations/preview/classic.html")

        # Minimal
        res_min = self.client.get(reverse("quotation_template_preview", kwargs={"pk": self.tpl_minimal_a.pk}))
        self.assertTemplateUsed(res_min, "quotations/preview/minimal.html")

    def test_preview_permission_gated(self):
        # User with quotation.view can preview
        self.client.login(username="prev_sales_a", password="password123")
        url = reverse("quotation_template_preview", kwargs={"pk": self.tpl_modern_a.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # User without view permissions is blocked (403)
        self.client.login(username="prev_unauth", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
