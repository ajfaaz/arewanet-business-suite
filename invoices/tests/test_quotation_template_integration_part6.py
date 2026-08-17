from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import ProtectedError

from invoices.models import Organization, Customer, Quotation, QuotationItem, QuotationTemplate, UserProfile
from invoices.forms import QuotationForm
from invoices.services.quotation_template_resolver import QuotationTemplateResolver
from sales.services.quotation_service import QuotationService


class QuotationTemplateIntegrationPart6TestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_part6", password="password123", email="admin_part6@example.com")
        self.client.login(username="admin_part6", password="password123")

        self.org_a = Organization.objects.create(
            name="Alpha Corp",
            slug="alpha-corp",
            currency="NGN",
            default_vat=Decimal("7.50")
        )
        UserProfile.objects.create(user=self.user, organization=self.org_a, role="ADMIN")

        self.org_b = Organization.objects.create(
            name="Beta Corp",
            slug="beta-corp",
            currency="USD"
        )

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Acme Clients Ltd",
            email="client@acme.com"
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

        self.tpl_inactive_a = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Inactive",
            style="minimal",
            is_active=False,
            is_default=False
        )

        # Template for Org B
        self.tpl_beta = QuotationTemplate.objects.create(
            organization=self.org_b,
            name="Beta Modern",
            style="modern",
            is_active=True,
            is_default=True
        )

    def test_new_quotation_saves_explicit_template(self):
        form_data = {
            'customer': self.customer_a.pk,
            'template': self.tpl_classic_a.pk,
            'quotation_date': '2026-08-17',
            'status': 'DRAFT',
            'vat': '7.50',
            'discount': '0.00'
        }
        form = QuotationForm(form_data, organization=self.org_a)
        self.assertTrue(form.is_valid(), form.errors)
        quotation = form.save(commit=False)
        quotation.organization = self.org_a
        quotation.save()

        self.assertEqual(quotation.template, self.tpl_classic_a)

    def test_new_quotation_uses_organization_default(self):
        q = Quotation(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-DEFAULT-001",
            quotation_date=date.today()
        )
        saved_q = QuotationService.create(q, items=[{'description': 'Item 1', 'qty': 1, 'unit_price': 100}], user=self.user)
        self.assertEqual(saved_q.template, self.tpl_modern_a)

    def test_historical_stability_on_default_change(self):
        # Create QT-1 under Org A default (Alpha Modern)
        q1 = Quotation(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-HIST-001",
            quotation_date=date.today()
        )
        q1 = QuotationService.create(q1, items=[], user=self.user)
        self.assertEqual(q1.template, self.tpl_modern_a)

        # Change Org A default template to Alpha Classic
        self.tpl_classic_a.is_default = True
        self.tpl_classic_a.save()

        # Create QT-2 under new default
        q2 = Quotation(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-HIST-002",
            quotation_date=date.today()
        )
        q2 = QuotationService.create(q2, items=[], user=self.user)

        # Historical Stability Check: QT-1 MUST remain Alpha Modern
        q1.refresh_from_db()
        self.assertEqual(q1.template, self.tpl_modern_a)
        self.assertEqual(q2.template, self.tpl_classic_a)

    def test_existing_null_template_resolves_default(self):
        # Existing historical quotation with template=NULL
        q_null = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-NULL-001",
            quotation_date=date.today(),
            template=None
        )

        resolved = QuotationTemplateResolver.resolve(self.org_a, quotation=q_null)
        self.assertEqual(resolved, self.tpl_modern_a)

        # Verify DB is NOT mutated by resolution
        q_null.refresh_from_db()
        self.assertIsNone(q_null.template)

    def test_tenant_isolation_rejects_cross_org_template(self):
        form_data = {
            'customer': self.customer_a.pk,
            'template': self.tpl_beta.pk, # Org B's template!
            'quotation_date': '2026-08-17',
            'status': 'DRAFT'
        }
        form = QuotationForm(form_data, organization=self.org_a)
        self.assertFalse(form.is_valid())
        self.assertIn('template', form.errors)

    def test_protect_on_delete_referenced_template(self):
        q = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-PROT-001",
            quotation_date=date.today(),
            template=self.tpl_classic_a
        )

        with self.assertRaises(ProtectedError):
            self.tpl_classic_a.delete()

        # Delete view post test
        url = reverse('quotation_template_delete', kwargs={'pk': self.tpl_classic_a.pk})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 302)
        # Template should still exist in database
        self.assertTrue(QuotationTemplate.objects.filter(pk=self.tpl_classic_a.pk).exists())

    def test_inactive_template_rejection(self):
        form_data = {
            'customer': self.customer_a.pk,
            'template': self.tpl_inactive_a.pk,
            'quotation_date': '2026-08-17',
            'status': 'DRAFT'
        }
        form = QuotationForm(form_data, organization=self.org_a)
        self.assertFalse(form.is_valid())

    def test_quotation_detail_displays_template(self):
        q = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-DETAIL-001",
            quotation_date=date.today(),
            template=self.tpl_classic_a
        )
        url = reverse('quotation_detail', kwargs={'pk': q.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Alpha Classic")

    def test_preview_resolves_quotation_template(self):
        q = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-PREV-001",
            quotation_date=date.today(),
            template=self.tpl_classic_a
        )
        url = reverse('quotation_template_preview', kwargs={'pk': 0}) + f"?quotation={q.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Alpha Classic")

    def test_preview_override_does_not_mutate_quotation(self):
        q = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-OVERRIDE-001",
            quotation_date=date.today(),
            template=self.tpl_modern_a
        )
        url = reverse('quotation_template_preview', kwargs={'pk': self.tpl_classic_a.pk}) + f"?quotation={q.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Alpha Classic")

        # Database record MUST remain Alpha Modern
        q.refresh_from_db()
        self.assertEqual(q.template, self.tpl_modern_a)

    def test_template_usage_count_in_list(self):
        Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            quotation_no="QT-COUNT-001",
            quotation_date=date.today(),
            template=self.tpl_classic_a
        )
        self.assertEqual(self.tpl_classic_a.quotations.count(), 1)
        self.assertEqual(self.tpl_modern_a.quotations.count(), 0)

        url = reverse('quotation_template_list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Alpha Classic")
