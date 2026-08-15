from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission

User = get_user_model()


class OrganizationPermissionsTestCase(TestCase):

    def setUp(self):
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_accountant = Role.objects.get(slug="accountant")
        self.role_sales = Role.objects.get(slug="sales-officer")

        self.org_a = Organization.objects.create(
            name="ArewaNet Ventures",
            slug="arewanet-ventures",
            email="info@arewanet.ng",
            phone="08020000000"
        )
        self.org_b = Organization.objects.create(
            name="Test Business Ltd",
            slug="test-business-ltd",
            email="contact@testbusiness.ng",
            phone="08030000000"
        )

        self.user_a = User.objects.create_user(username="user_a", email="user_a@test.com", password="password123")
        self.user_b = User.objects.create_user(username="user_b", email="user_b@test.com", password="password123")

    def test_permission_creation_and_lookup(self):
        codes = ["customer.view", "invoice.create", "grn.approve", "stock_adjustment.approve"]
        for code in codes:
            perm = Permission.objects.get(code=code)
            self.assertTrue(perm.is_active)
            self.assertIsNotNone(perm.name)
            self.assertIsNotNone(perm.module)

    def test_role_permission_assignment(self):
        # Administrator should have invoice.create and stock_adjustment.approve
        self.assertTrue(self.role_admin.permissions.filter(code="invoice.create").exists())
        self.assertTrue(self.role_admin.permissions.filter(code="stock_adjustment.approve").exists())

        # Sales Officer should have quotation.create but NOT stock_adjustment.approve
        self.assertTrue(self.role_sales.permissions.filter(code="quotation.create").exists())
        self.assertFalse(self.role_sales.permissions.filter(code="stock_adjustment.approve").exists())

    def test_membership_has_permission_active(self):
        m_admin = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        self.assertTrue(m_admin.has_permission("invoice.create"))
        self.assertTrue(m_admin.has_permission("customer.view"))

        m_sales = OrganizationMembership.objects.create(user=self.user_b, organization=self.org_a, role=self.role_sales)
        self.assertTrue(m_sales.has_permission("quotation.create"))
        self.assertFalse(m_sales.has_permission("inventory.adjustment.approve"))

    def test_inactive_membership(self):
        m = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin, is_active=False)
        self.assertFalse(m.has_permission("invoice.create"))

    def test_inactive_role(self):
        role_inactive = Role.objects.create(name="Inactive Role", slug="inactive-role", is_active=False)
        role_inactive.permissions.add(Permission.objects.get(code="invoice.create"))

        m = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=role_inactive)
        self.assertFalse(m.has_permission("invoice.create"))

    def test_inactive_permission(self):
        m = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_sales)
        perm = Permission.objects.get(code="quotation.create")

        self.assertTrue(m.has_permission("quotation.create"))

        # Deactivate permission
        perm.is_active = False
        perm.save()

        self.assertFalse(m.has_permission("quotation.create"))

    def test_cross_organization_permissions(self):
        # User A is Admin in Org A, Accountant in Org B
        m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        m_b = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=self.role_accountant)

        # In Org A (Admin), User A can delete invoices
        self.assertTrue(m_a.has_permission("invoice.delete"))

        # In Org B (Accountant), User A CANNOT delete invoices
        self.assertFalse(m_b.has_permission("invoice.delete"))
