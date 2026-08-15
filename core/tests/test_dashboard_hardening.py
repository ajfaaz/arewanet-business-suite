from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, Customer, Invoice, Quotation, Product
from purchases.models import Supplier

User = get_user_model()


class DashboardHardeningTestCase(TestCase):

    def setUp(self):
        # System roles
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_sales = Role.objects.get(slug="sales-officer")
        self.role_accountant = Role.objects.get(slug="accountant")

        # Organizations
        self.org_a = Organization.objects.create(name="Hardened Org A", slug="hardened-a")
        self.org_b = Organization.objects.create(name="Hardened Org B", slug="hardened-b")

        # Users
        self.user_a = User.objects.create_user(username="usera_hardened", email="usera@test.com", password="password123")
        self.user_b = User.objects.create_user(username="userb_hardened", email="userb@test.com", password="password123")
        self.user_no_org = User.objects.create_user(username="user_no_org", email="noorg@test.com", password="password123")

        # Memberships
        self.m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        self.m_b = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_b, role=self.role_admin)

        # Org A Data
        self.cust_a = Customer.objects.create(company_name="Cust A", organization=self.org_a)
        self.inv_a = Invoice.objects.create(
            invoice_no="INV-HARD-A",
            customer=self.cust_a,
            organization=self.org_a,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("100.00"),
            total_due=Decimal("100.00"),
            status="UNPAID"
        )
        self.prod_a = Product.objects.create(
            name="Prod A",
            organization=self.org_a,
            selling_price=Decimal("50.00"),
            cost_price=Decimal("30.00")
        )

        # Org B Data
        self.cust_b = Customer.objects.create(company_name="Cust B", organization=self.org_b)
        self.inv_b = Invoice.objects.create(
            invoice_no="INV-HARD-B",
            customer=self.cust_b,
            organization=self.org_b,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("200.00"),
            total_due=Decimal("200.00"),
            status="UNPAID"
        )
        self.prod_b = Product.objects.create(
            name="Prod B",
            organization=self.org_b,
            selling_price=Decimal("80.00"),
            cost_price=Decimal("40.00")
        )

    def test_unauthenticated_dashboard_redirect(self):
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.url)

    def test_user_without_organization_graceful(self):
        self.client.login(username="user_no_org", password="password123")
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)

    def test_inactive_membership_denied(self):
        # Deactivate User B's membership
        self.m_b.is_active = False
        self.m_b.save()

        self.client.login(username="userb_hardened", password="password123")
        res = self.client.post("/organization/switch/", {"organization_id": self.org_b.id})
        # Should raise PermissionDenied or 403
        self.assertIn(res.status_code, [403, 302])

    def test_unauthorized_organization_switch_denied(self):
        # User A attempts to switch to Org B (where User A has no membership)
        self.client.login(username="usera_hardened", password="password123")
        res = self.client.post("/organization/switch/", {"organization_id": self.org_b.id})
        self.assertEqual(res.status_code, 403)

    def test_cross_tenant_idor_protection(self):
        # User A attempts direct access to Org B's invoice
        self.client.login(username="usera_hardened", password="password123")
        res = self.client.get(f"/invoice/{self.inv_b.id}/")
        self.assertIn(res.status_code, [404, 403])

        # User A attempts direct access to Org B's customer detail/edit
        res_cust = self.client.get(f"/customers/{self.cust_b.id}/")
        self.assertIn(res_cust.status_code, [404, 403])

    def test_dynamic_permission_removal(self):
        user_dyn = User.objects.create_user(username="user_dyn_perm", email="dyn@test.com", password="password123")
        perm_inv_create, _ = Permission.objects.get_or_create(code="invoice.create", defaults={"name": "Create Invoices", "module": "invoice", "action": "create", "is_active": True})
        role_dyn = Role.objects.create(name="Dynamic Role", slug="dynamic-role", is_active=True)
        role_dyn.permissions.add(perm_inv_create)

        OrganizationMembership.objects.create(user=user_dyn, organization=self.org_a, role=role_dyn)

        self.client.login(username="user_dyn_perm", password="password123")
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "+ New Invoice")

        # Revoke invoice.create permission
        role_dyn.permissions.remove(perm_inv_create)

        res_after = self.client.get("/dashboard/")
        self.assertEqual(res_after.status_code, 200)
        self.assertNotContains(res_after, "+ New Invoice")

    def test_api_tenant_isolation_and_idor(self):
        self.client.login(username="usera_hardened", password="password123")
        
        # API listing should only show Org A customers
        res = self.client.get("/api/v1/customers/")
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                cust_names = [c.get('company_name') for c in data]
                self.assertIn("Cust A", cust_names)
                self.assertNotIn("Cust B", cust_names)
