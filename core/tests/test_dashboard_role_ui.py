from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission
from invoices.navigation import get_user_menu

User = get_user_model()


class DashboardRoleUITestCase(TestCase):

    def setUp(self):
        # Retrieve system roles
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_sales = Role.objects.get(slug="sales-officer")
        self.role_accountant = Role.objects.get(slug="accountant")
        self.role_inventory = Role.objects.get(slug="inventory-officer")

        # Create two distinct organizations
        self.org_a = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet")
        self.org_b = Organization.objects.create(name="ABC Trading Ltd", slug="abc-trading")

        # Create users
        self.user_admin = User.objects.create_user(username="adminuser", password="password123")
        self.user_sales = User.objects.create_user(username="salesuser", password="password123")
        self.user_inventory = User.objects.create_user(username="inventoryuser", password="password123")
        self.user_multi = User.objects.create_user(username="multiuser", password="password123")

        # Memberships
        self.m_admin = OrganizationMembership.objects.create(user=self.user_admin, organization=self.org_a, role=self.role_admin)
        self.m_sales = OrganizationMembership.objects.create(user=self.user_sales, organization=self.org_a, role=self.role_sales)
        self.m_inventory = OrganizationMembership.objects.create(user=self.user_inventory, organization=self.org_a, role=self.role_inventory)

        # Multi-org user: Org A = Administrator, Org B = Accountant
        self.m_multi_a = OrganizationMembership.objects.create(user=self.user_multi, organization=self.org_a, role=self.role_admin)
        self.m_multi_b = OrganizationMembership.objects.create(user=self.user_multi, organization=self.org_b, role=self.role_accountant)

    def test_administrator_menu_sections(self):
        sections = get_user_menu(self.m_admin)
        titles = [s['title'] for s in sections]
        self.assertIn("Sales & Revenue", titles)
        self.assertIn("Purchasing", titles)
        self.assertIn("Inventory & Operations", titles)
        self.assertIn("Finance", titles)
        self.assertIn("System", titles)

    def test_sales_officer_menu_sections(self):
        sections = get_user_menu(self.m_sales)
        titles = [s['title'] for s in sections]
        self.assertIn("Sales & Revenue", titles)
        # Empty sections without permitted items are hidden
        self.assertNotIn("Inventory & Operations", titles)
        self.assertNotIn("System", titles)

    def test_inventory_officer_menu_sections(self):
        sections = get_user_menu(self.m_inventory)
        titles = [s['title'] for s in sections]
        self.assertIn("Inventory & Operations", titles)
        self.assertNotIn("Sales & Revenue", titles)
        self.assertNotIn("System", titles)

    def test_custom_role_warehouse_manager(self):
        # Create a custom role "Warehouse Manager" with product.view
        custom_role = Role.objects.create(name="Warehouse Manager", slug="warehouse-manager", is_active=True)
        perm_product_view, _ = Permission.objects.get_or_create(code="product.view", defaults={"name": "View Products", "module": "product", "action": "view", "is_active": True})
        perm_product_view.is_active = True
        perm_product_view.save()
        custom_role.permissions.add(perm_product_view)

        m_custom = OrganizationMembership.objects.create(user=self.user_sales, organization=self.org_b, role=custom_role)
        sections = get_user_menu(m_custom)
        titles = [s['title'] for s in sections]

        self.assertIn("Inventory & Operations", titles)
        self.assertNotIn("Sales & Revenue", titles)

    def test_cross_organization_dashboard_switch(self):
        # User Multi logged in, starting in Org A (Administrator)
        self.client.login(username="multiuser", password="password123")
        res_a = self.client.get("/dashboard/")
        self.assertEqual(res_a.status_code, 200)
        self.assertContains(res_a, "Administrator")
        self.assertContains(res_a, "Customers")
        self.assertContains(res_a, "+ New Customer")

        # Switch active organization to Org B (Accountant)
        switch_res = self.client.post("/organization/switch/", {"organization_id": self.org_b.id})
        self.assertEqual(switch_res.status_code, 302)

        res_b = self.client.get("/dashboard/")
        self.assertEqual(res_b.status_code, 200)
        self.assertContains(res_b, "Accountant")
        self.assertContains(res_b, "Total Invoiced")
        self.assertNotContains(res_b, "Inventory &amp; Operations")
