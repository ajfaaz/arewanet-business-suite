from django.test import TestCase, Client
from django.contrib.auth.models import User
from invoices.models import Organization, OrganizationMembership, Role, Permission


class PermissionDeniedUITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="restricted_user",
            email="restricted@example.com",
            password="Password123!"
        )
        self.org = Organization.objects.create(name="Acme Corp")
        self.role = Role.objects.create(
            name="Limited Viewer",
            slug="limited-viewer"
        )
        # Grant only customer.view permission, NOT quotation_template.create or role.view
        p_customer_view = Permission.objects.filter(code="customer.view").first()
        if p_customer_view:
            self.role.permissions.add(p_customer_view)

        self.membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=self.role,
            is_active=True
        )
        self.client.login(username="restricted_user", password="Password123!")
        session = self.client.session
        session['active_organization_id'] = self.org.id
        session.save()

    def test_restricted_page_access_renders_professional_403_page(self):
        """
        Verifies that accessing a page without required role permissions
        returns HTTP 403 and renders the professional '403.html' page.
        """
        # Attempt to access quotation template creation page (requires quotation_template.create)
        response = self.client.get('/quotation-templates/create/')
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertContains(response, "Access Restricted", status_code=403)
        self.assertContains(response, "Permission Required", status_code=403)
        self.assertContains(response, "Limited Viewer", status_code=403)
        self.assertContains(response, "Return to Dashboard", status_code=403)

    def test_direct_handler_invocation_renders_custom_exception_message(self):
        """
        Directly tests custom_permission_denied view with an exception message.
        """
        from invoices.views import custom_permission_denied
        from django.core.exceptions import PermissionDenied

        request = self.client.get('/quotation-templates/create/').wsgi_request
        request.user = self.user
        request.session = {'active_organization_id': self.org.id}

        exc = PermissionDenied("You do not have permission (quotation_template.create) to view this page.")
        response = custom_permission_denied(request, exception=exc)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access Restricted", status_code=403)
        self.assertContains(response, "quotation_template.create", status_code=403)
