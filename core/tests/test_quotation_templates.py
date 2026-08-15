from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, Customer, Quotation, QuotationTemplate
from invoices.services.quotation_template_service import QuotationTemplateService
from invoices.services.template_renderer import QuotationTemplateRenderer

User = get_user_model()


class QuotationTemplateTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(name="Template Org A", slug="template-org-a")
        self.org_b = Organization.objects.create(name="Template Org B", slug="template-org-b")

        self.role_admin = Role.objects.get(slug="administrator")
        self.role_sales = Role.objects.get(slug="sales-officer")

        self.user_a = User.objects.create_user(username="tpl_user_a", password="password123")
        self.m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)

        self.tpl_a1 = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Modern Org A",
            style="modern",
            is_active=True,
            is_default=True
        )
        self.tpl_a2 = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Classic Org A",
            style="classic",
            is_active=True,
            is_default=False
        )

        self.tpl_b1 = QuotationTemplate.objects.create(
            organization=self.org_b,
            name="Corporate Org B",
            style="minimal",
            is_active=True,
            is_default=True
        )

    def test_template_organization_isolation(self):
        service_a = QuotationTemplateService(self.org_a)
        service_b = QuotationTemplateService(self.org_b)

        templates_a = service_a.get_templates()
        templates_b = service_b.get_templates()

        self.assertEqual(templates_a.count(), 2)
        self.assertIn(self.tpl_a1, templates_a)
        self.assertNotIn(self.tpl_b1, templates_a)

        self.assertEqual(templates_b.count(), 1)
        self.assertIn(self.tpl_b1, templates_b)
        self.assertNotIn(self.tpl_a1, templates_b)

    def test_cross_tenant_template_retrieval_blocked(self):
        service_a = QuotationTemplateService(self.org_a)
        # Attempting to fetch Org B's template under Org A service should return None
        fetched_b = service_a.get_template(self.tpl_b1.id)
        self.assertIsNone(fetched_b)

    def test_single_default_template_per_organization(self):
        service_a = QuotationTemplateService(self.org_a)
        
        # Initially tpl_a1 is default
        self.assertTrue(QuotationTemplate.objects.get(id=self.tpl_a1.id).is_default)
        self.assertFalse(QuotationTemplate.objects.get(id=self.tpl_a2.id).is_default)

        # Set tpl_a2 as default
        service_a.set_default_template(self.tpl_a2.id)

        self.assertFalse(QuotationTemplate.objects.get(id=self.tpl_a1.id).is_default)
        self.assertTrue(QuotationTemplate.objects.get(id=self.tpl_a2.id).is_default)

    def test_inactive_template_cannot_be_selected(self):
        self.tpl_a2.is_active = False
        self.tpl_a2.save()

        service_a = QuotationTemplateService(self.org_a)
        template = service_a.get_template(self.tpl_a2.id, active_only=True)
        self.assertIsNone(template)

    def test_template_renderer_context_assembly(self):
        cust = Customer.objects.create(company_name="Quote Client", organization=self.org_a)
        quote = Quotation.objects.create(
            quotation_no="QT-2026-TEST",
            customer=cust,
            organization=self.org_a,
            quotation_date=date.today(),
            subtotal=Decimal("50000.00"),
            total=Decimal("50000.00")
        )

        renderer = QuotationTemplateRenderer(organization=self.org_a)
        context = renderer.render_context(quote, self.tpl_a1)

        self.assertEqual(context['quotation'], quote)
        self.assertEqual(context['organization'], self.org_a)
        self.assertEqual(context['customer'], cust)
        self.assertEqual(context['template'], self.tpl_a1)
        self.assertEqual(context['style'], "modern")

    def test_template_permission_enforcement(self):
        perm_view, _ = Permission.objects.get_or_create(code="quotation_template.view", defaults={"name": "View Templates", "module": "quotation_template", "action": "view"})
        perm_create, _ = Permission.objects.get_or_create(code="quotation_template.create", defaults={"name": "Create Templates", "module": "quotation_template", "action": "create"})

        role_restricted = Role.objects.create(name="Template Viewer", slug="template-viewer", is_active=True)
        role_restricted.permissions.add(perm_view)

        m_restricted = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=role_restricted)

        self.assertTrue(m_restricted.has_permission("quotation_template.view"))
        self.assertFalse(m_restricted.has_permission("quotation_template.create"))
