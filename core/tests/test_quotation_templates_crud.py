from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, QuotationTemplate

User = get_user_model()


class QuotationTemplateCRUDTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(name="CRUD Org A", slug="crud-org-a")
        self.org_b = Organization.objects.create(name="CRUD Org B", slug="crud-org-b")

        self.role_admin = Role.objects.get(slug="administrator")

        # Create permissions
        self.perm_view, _ = Permission.objects.get_or_create(code="quotation_template.view", defaults={"name": "View", "module": "quotation_template", "action": "view"})
        self.perm_create, _ = Permission.objects.get_or_create(code="quotation_template.create", defaults={"name": "Create", "module": "quotation_template", "action": "create"})
        self.perm_edit, _ = Permission.objects.get_or_create(code="quotation_template.edit", defaults={"name": "Edit", "module": "quotation_template", "action": "edit"})
        self.perm_delete, _ = Permission.objects.get_or_create(code="quotation_template.delete", defaults={"name": "Delete", "module": "quotation_template", "action": "delete"})
        self.perm_set_default, _ = Permission.objects.get_or_create(code="quotation_template.set_default", defaults={"name": "Set Default", "module": "quotation_template", "action": "set_default"})

        # Admin user for Org A
        self.user_a = User.objects.create_user(username="crud_admin_a", password="password123")
        self.m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)

        # Restricted user for Org A (view only)
        self.role_viewer = Role.objects.create(name="Template Viewer", slug="template-viewer", is_active=True)
        self.role_viewer.permissions.add(self.perm_view)
        self.user_viewer = User.objects.create_user(username="crud_viewer_a", password="password123")
        self.m_viewer = OrganizationMembership.objects.create(user=self.user_viewer, organization=self.org_a, role=self.role_viewer)

        # Admin user for Org B
        self.user_b = User.objects.create_user(username="crud_admin_b", password="password123")
        self.m_b = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_b, role=self.role_admin)

        # Templates
        self.tpl_a1 = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Template A1 Modern",
            style="modern",
            is_active=True,
            is_default=True
        )
        self.tpl_a2 = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Template A2 Classic",
            style="classic",
            is_active=True,
            is_default=False
        )

        self.tpl_b1 = QuotationTemplate.objects.create(
            organization=self.org_b,
            name="Template B1 Minimal",
            style="minimal",
            is_active=True,
            is_default=True
        )

    def test_template_list_organization_scoping(self):
        self.client.login(username="crud_admin_a", password="password123")
        response = self.client.get(reverse("quotation_template_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Template A1 Modern")
        self.assertContains(response, "Template A2 Classic")
        self.assertNotContains(response, "Template B1 Minimal")

    def test_template_create_auto_assign_organization(self):
        self.client.login(username="crud_admin_a", password="password123")
        post_data = {
            "name": "Template A3 Custom",
            "description": "Custom created template for Org A",
            "style": "minimal",
            "is_active": True,
            "is_default": False
        }
        response = self.client.post(reverse("quotation_template_create"), post_data)
        self.assertEqual(response.status_code, 302)

        created = QuotationTemplate.objects.get(name="Template A3 Custom")
        self.assertEqual(created.organization, self.org_a)
        self.assertEqual(created.style, "minimal")

    def test_template_edit_cross_tenant_denied(self):
        self.client.login(username="crud_admin_a", password="password123")
        # Attempt to edit Org B's template using Org A admin credentials
        url = reverse("quotation_template_edit", kwargs={"pk": self.tpl_b1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        post_data = {
            "name": "Hacked Template Name",
            "style": "modern",
            "is_active": True
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 404)

        # Verify Org B's template remains unchanged
        self.tpl_b1.refresh_from_db()
        self.assertEqual(self.tpl_b1.name, "Template B1 Minimal")

    def test_set_default_atomic_tenant_isolation(self):
        self.client.login(username="crud_admin_a", password="password123")
        url = reverse("quotation_template_set_default", kwargs={"pk": self.tpl_a2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.tpl_a1.refresh_from_db()
        self.tpl_a2.refresh_from_db()
        self.tpl_b1.refresh_from_db()

        # Org A defaults switched
        self.assertFalse(self.tpl_a1.is_default)
        self.assertTrue(self.tpl_a2.is_default)

        # Org B default untouched
        self.assertTrue(self.tpl_b1.is_default)

    def test_deactivate_current_default_blocked(self):
        self.client.login(username="crud_admin_a", password="password123")
        url = reverse("quotation_template_toggle_active", kwargs={"pk": self.tpl_a1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Verify tpl_a1 remains active because it is default
        self.tpl_a1.refresh_from_db()
        self.assertTrue(self.tpl_a1.is_active)
        self.assertTrue(self.tpl_a1.is_default)

    def test_permission_gated_crud_actions(self):
        self.client.login(username="crud_viewer_a", password="password123")

        # View list works
        response = self.client.get(reverse("quotation_template_list"))
        self.assertEqual(response.status_code, 200)

        # Create blocked (403)
        response = self.client.get(reverse("quotation_template_create"))
        self.assertEqual(response.status_code, 403)

        # Edit blocked (403)
        response = self.client.get(reverse("quotation_template_edit", kwargs={"pk": self.tpl_a1.pk}))
        self.assertEqual(response.status_code, 403)

        # Set default blocked (403)
        response = self.client.get(reverse("quotation_template_set_default", kwargs={"pk": self.tpl_a2.pk}))
        self.assertEqual(response.status_code, 403)

        # Delete blocked (403)
        response = self.client.get(reverse("quotation_template_delete", kwargs={"pk": self.tpl_a2.pk}))
        self.assertEqual(response.status_code, 403)
