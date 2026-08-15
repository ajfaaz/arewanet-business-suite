from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.contrib.sessions.middleware import SessionMiddleware
from invoices.models import Organization, OrganizationMembership, Role, Customer, Invoice
from invoices.forms import InvoiceForm
from invoices.views import switch_organization, invoice_detail, customer_detail
from core.context import get_organization_context
from core.middleware import OrganizationContextMiddleware

User = get_user_model()


class TenantIsolationTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.role_admin = Role.objects.get(slug="administrator")
        self.role_accountant = Role.objects.get(slug="accountant")

        # Create two distinct organizations
        self.org_a = Organization.objects.create(name="Org A Ventures", slug="org-a", email="a@test.com")
        self.org_b = Organization.objects.create(name="Org B Trading", slug="org-b", email="b@test.com")

        # Create users
        self.user_a = User.objects.create_user(username="user_a", email="user_a@test.com", password="password123")
        self.user_b = User.objects.create_user(username="user_b", email="user_b@test.com", password="password123")

        # User A belongs ONLY to Org A
        self.m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)

        # User B belongs ONLY to Org B
        self.m_b = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_b, role=self.role_admin)

        # Create customers
        self.cust_a = Customer.objects.create(company_name="Customer A", organization=self.org_a)
        self.cust_b = Customer.objects.create(company_name="Customer B", organization=self.org_b)

        from datetime import date
        # Create invoices
        self.inv_a = Invoice.objects.create(invoice_no="INV-A-001", customer=self.cust_a, organization=self.org_a, invoice_date=date.today(), due_date=date.today())
        self.inv_b = Invoice.objects.create(invoice_no="INV-B-001", customer=self.cust_b, organization=self.org_b, invoice_date=date.today(), due_date=date.today())

    def test_context_resolution(self):
        req = self.factory.get("/")
        req.user = self.user_a

        # Add session support to dummy request
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(req)

        ctx = get_organization_context(req)
        self.assertEqual(ctx.organization, self.org_a)
        self.assertEqual(ctx.membership, self.m_a)
        self.assertEqual(ctx.role, self.role_admin)

    def test_tenant_queryset_isolation_in_views(self):
        # User A trying to access Invoice A -> 200 OK
        self.client.login(username="user_a", password="password123")
        res_a = self.client.get(f"/invoice/{self.inv_a.id}/")
        self.assertEqual(res_a.status_code, 200)

        # User A trying to access Invoice B (Org B) -> 404 Not Found
        res_b = self.client.get(f"/invoice/{self.inv_b.id}/")
        self.assertEqual(res_b.status_code, 404)

    def test_customer_detail_isolation(self):
        self.client.login(username="user_a", password="password123")

        # Customer A -> 200 OK
        res_a = self.client.get(f"/customers/{self.cust_a.id}/")
        self.assertEqual(res_a.status_code, 200)

        # Customer B (Org B) -> 404 Not Found
        res_b = self.client.get(f"/customers/{self.cust_b.id}/")
        self.assertEqual(res_b.status_code, 404)

    def test_cross_tenant_relationship_rejection(self):
        # Attempting to create an Invoice in Org A linked to Customer B (Org B)
        form_data = {
            "customer": self.cust_b.id,
            "invoice_date": "2026-08-15",
            "due_date": "2026-08-30",
            "status": "DRAFT",
            "vat": 7.5,
        }
        form = InvoiceForm(data=form_data, organization=self.org_a)
        self.assertFalse(form.is_valid())
        self.assertIn("customer", form.errors)

    def test_organization_switcher_authorized(self):
        # Add User A to Org B as Accountant
        OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=self.role_accountant)

        self.client.login(username="user_a", password="password123")

        # Switch to Org B
        res = self.client.post("/organization/switch/", {"organization_id": self.org_b.id})
        self.assertEqual(res.status_code, 302)

        # Check session updated
        self.assertEqual(self.client.session.get("active_organization_id"), self.org_b.id)

    def test_organization_switcher_unauthorized(self):
        self.client.login(username="user_a", password="password123")

        # Attempt to switch to Org B (where User A is NOT a member) -> PermissionDenied 403
        res = self.client.post("/organization/switch/", {"organization_id": self.org_b.id})
        self.assertEqual(res.status_code, 403)
