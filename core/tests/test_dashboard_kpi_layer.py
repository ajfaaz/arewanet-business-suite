from decimal import Decimal
from datetime import date
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, Customer, Invoice, Quotation, Product
from invoices.services.dashboard_service import DashboardService

User = get_user_model()


class DashboardKPILayerTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        # Retrieve system roles
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_accountant = Role.objects.get(slug="accountant")

        # Create two distinct organizations
        self.org_a = Organization.objects.create(name="Org A Ventures", slug="org-a")
        self.org_b = Organization.objects.create(name="Org B Enterprise", slug="org-b")
        self.org_empty = Organization.objects.create(name="Empty Startup Ltd", slug="org-empty")

        # Create users
        self.user_a = User.objects.create_user(username="usera", email="usera@test.com", password="password123")
        self.user_b = User.objects.create_user(username="userb", email="userb@test.com", password="password123")

        # User A in Org A (Admin) and Org B (Accountant)
        self.m_a1 = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        self.m_a2 = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=self.role_accountant)

        # Populate Org A: 10 customers, 1 invoice of NGN 1,000,000
        for i in range(10):
            Customer.objects.create(company_name=f"Customer A{i}", organization=self.org_a)

        c_a = Customer.objects.first()
        Invoice.objects.create(
            invoice_no="INV-A-100",
            customer=c_a,
            organization=self.org_a,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("1000000.00"),
            total_due=Decimal("1000000.00"),
            status="UNPAID"
        )

        # Populate Org B: 50 customers, 1 invoice of NGN 20,000,000
        for i in range(50):
            Customer.objects.create(company_name=f"Customer B{i}", organization=self.org_b)

        c_b = Customer.objects.filter(organization=self.org_b).first()
        Invoice.objects.create(
            invoice_no="INV-B-200",
            customer=c_b,
            organization=self.org_b,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("20000000.00"),
            total_due=Decimal("20000000.00"),
            status="UNPAID"
        )

    def test_kpi_multi_tenant_isolation(self):
        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        kpi_a = service_a.get_dashboard_data()
        kpi_b = service_b.get_dashboard_data()

        self.assertEqual(kpi_a['kpis']['customers']['count'], 10)
        self.assertEqual(kpi_a['kpis']['invoices']['total_invoiced'], "₦1,000,000.00")

        self.assertEqual(kpi_b['kpis']['customers']['count'], 50)
        self.assertEqual(kpi_b['kpis']['invoices']['total_invoiced'], "₦20,000,000.00")

    def test_empty_organization_safe_defaults(self):
        service_empty = DashboardService(self.org_empty)
        data = service_empty.get_dashboard_data()

        self.assertEqual(data['kpis']['customers']['count'], 0)
        self.assertEqual(data['kpis']['invoices']['total_invoiced'], "₦0.00")
        self.assertEqual(data['kpis']['invoices']['outstanding'], "₦0.00")
        self.assertEqual(data['kpis']['payments']['total_received'], "₦0.00")

    def test_custom_role_permission_based_kpi_omission(self):
        # Create a custom role "Stock Manager" with ONLY product permissions
        custom_role = Role.objects.create(name="Stock Manager", slug="stock-manager", is_active=True)
        perm_product_view, _ = Permission.objects.get_or_create(code="product.view", defaults={"name": "View Products", "module": "product", "action": "view", "is_active": True})
        perm_product_view.is_active = True
        perm_product_view.save()
        custom_role.permissions.add(perm_product_view)

        m_custom = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_a, role=custom_role)

        service = DashboardService(self.org_a)
        data = service.get_dashboard_data(membership=m_custom)

        self.assertTrue(data['kpis']['show_products'])
        self.assertFalse(data['kpis']['show_invoices'])
        self.assertFalse(data['kpis']['show_customers'])
        self.assertNotIn('invoices', data['kpis'])
        self.assertNotIn('customers', data['kpis'])

        # Render dashboard view as User B
        self.client.login(username="userb", password="password123")
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Products")
        self.assertNotContains(res, "Total Invoiced")

    def test_recent_activity_tenant_isolation(self):
        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        activity_a = service_a.get_recent_activity()
        activity_b = service_b.get_recent_activity()

        self.assertEqual(len(activity_a['invoices']), 1)
        self.assertEqual(activity_a['invoices'][0].invoice_no, "INV-A-100")

        self.assertEqual(len(activity_b['invoices']), 1)
        self.assertEqual(activity_b['invoices'][0].invoice_no, "INV-B-200")
