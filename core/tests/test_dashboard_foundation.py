from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Customer, Invoice
from invoices.services.dashboard_service import DashboardService
from datetime import date

User = get_user_model()


class DashboardFoundationTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.role_admin = Role.objects.get(slug="administrator")
        self.role_accountant = Role.objects.get(slug="accountant")
        self.role_sales = Role.objects.get(slug="sales-officer")

        # Create Organizations
        self.org_a = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet-ventures")
        self.org_b = Organization.objects.create(name="ABC Trading Ltd", slug="abc-trading")

        # Create Users
        self.user_a = User.objects.create_user(username="user_a", email="user_a@test.com", password="password123")
        self.user_b = User.objects.create_user(username="user_b", email="user_b@test.com", password="password123")

        # Memberships: User A in Org A (Admin) & Org B (Accountant)
        self.m_a1 = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        self.m_a2 = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=self.role_accountant)

        # User B in Org A (Sales Officer)
        self.m_b1 = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_a, role=self.role_sales)

        # Seed Customers & Invoices in Org A (5 customers)
        for i in range(5):
            c = Customer.objects.create(company_name=f"Org A Client {i}", organization=self.org_a)
            Invoice.objects.create(invoice_no=f"INV-A-{i}", customer=c, organization=self.org_a, invoice_date=date.today(), due_date=date.today(), total_due=1000)

        # Seed Customers in Org B (12 customers)
        for i in range(12):
            Customer.objects.create(company_name=f"Org B Client {i}", organization=self.org_b)

    def test_unauthenticated_dashboard_redirect(self):
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login/", res.url)

    def test_dashboard_loads_for_authenticated_member(self):
        self.client.login(username="user_a", password="password123")
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "ArewaNet Ventures")

    def test_dashboard_kpi_tenant_isolation(self):
        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        self.assertEqual(service_a.get_customer_count(), 5)
        self.assertEqual(service_b.get_customer_count(), 12)

    def test_dashboard_organization_switcher_changes_kpi(self):
        self.client.login(username="user_a", password="password123")

        # Initial Org A dashboard -> 5 customers
        res_a = self.client.get("/dashboard/")
        self.assertEqual(res_a.context["customer_count"], 5)

        # Switch to Org B
        self.client.post("/organization/switch/", {"organization_id": self.org_b.id})

        # Switched Org B dashboard -> 12 customers
        res_b = self.client.get("/dashboard/")
        self.assertEqual(res_b.context["customer_count"], 12)
        self.assertContains(res_b, "ABC Trading Ltd")

    def test_dashboard_role_permission_navigation_filtering(self):
        self.client.login(username="user_b", password="password123")
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["role"], self.role_sales)
