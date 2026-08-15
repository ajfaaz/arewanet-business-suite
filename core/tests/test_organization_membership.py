from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from invoices.models import Organization, OrganizationMembership, Role

User = get_user_model()


class OrganizationMembershipTestCase(TestCase):

    def setUp(self):
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_accountant = Role.objects.get(slug="accountant")

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
        self.user_c = User.objects.create_user(username="user_c", email="user_c@test.com", password="password123")

    def test_system_roles_exist(self):
        slugs = ["administrator", "accountant", "sales-officer", "inventory-officer", "purchase-officer"]
        for slug in slugs:
            role = Role.objects.get(slug=slug)
            self.assertTrue(role.is_system_role)
            self.assertTrue(role.is_active)

    def test_role_slug_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Role.objects.create(name="Duplicate Admin", slug="administrator")

    def test_membership_creation_with_role(self):
        m1 = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        self.assertTrue(m1.is_active)
        self.assertEqual(m1.role, self.role_admin)
        self.assertEqual(self.user_a.organization_memberships.count(), 1)
        self.assertEqual(self.org_a.memberships.count(), 1)
        self.assertIn(m1, self.org_a.memberships.all())

    def test_duplicate_membership_protection(self):
        OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        with self.assertRaises(IntegrityError):
            OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_accountant)

    def test_same_user_different_organizations_different_roles(self):
        # User A -> Org A -> Administrator
        # User A -> Org B -> Accountant
        m_a = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        m_b = OrganizationMembership.objects.create(user=self.user_a, organization=self.org_b, role=self.role_accountant)

        self.assertEqual(m_a.role, self.role_admin)
        self.assertEqual(m_b.role, self.role_accountant)

        user_memberships = list(self.user_a.organization_memberships.all())
        self.assertEqual(len(user_memberships), 2)
        self.assertEqual(self.user_a.organization_memberships.get(organization=self.org_a).role, self.role_admin)
        self.assertEqual(self.user_a.organization_memberships.get(organization=self.org_b).role, self.role_accountant)

    def test_multiple_users_per_organization(self):
        # Organization A has User A (Admin) and User B (Accountant)
        OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        OrganizationMembership.objects.create(user=self.user_b, organization=self.org_a, role=self.role_accountant)

        org_users = [m.user for m in self.org_a.memberships.filter(is_active=True)]
        self.assertEqual(len(org_users), 2)
        self.assertIn(self.user_a, org_users)
        self.assertIn(self.user_b, org_users)
        self.assertNotIn(self.user_c, org_users)

    def test_protected_role_deletion(self):
        # Role assigned to membership cannot be deleted
        OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        with self.assertRaises(ProtectedError):
            self.role_admin.delete()

    def test_cascade_deletion_organization(self):
        OrganizationMembership.objects.create(user=self.user_a, organization=self.org_a, role=self.role_admin)
        initial_count = OrganizationMembership.objects.count()

        self.org_a.delete()
        self.assertEqual(OrganizationMembership.objects.count(), initial_count - 1)

