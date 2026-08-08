from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, UserProfile, Product
from core.permissions import IsOrganizationMember, IsOrganizationAdmin

User = get_user_model()


class OrganizationPermissionsTestCase(TestCase):

    def setUp(self):
        # Organization A setup
        self.org_a = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet-ventures")
        self.user_a = User.objects.create_user(username="usera", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="STAFF")
        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Customer A",
            email="customera@arewanet.com"
        )

        # Organization Admin setup for Org A
        self.admin_user_a = User.objects.create_user(username="admina", password="password123")
        self.admin_profile_a = UserProfile.objects.create(user=self.admin_user_a, organization=self.org_a, role="ADMIN")

        # Organization B setup
        self.org_b = Organization.objects.create(name="ABC Technologies", slug="abc-technologies")
        self.user_b = User.objects.create_user(username="userb", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="STAFF")
        self.customer_b = Customer.objects.create(
            organization=self.org_b,
            company_name="Customer B",
            email="customerb@abctech.com"
        )

        # User without an organization
        self.no_org_user = User.objects.create_user(username="noorguser", password="password123")

        self.client = APIClient()

    def test_1_authenticated_user_with_organization_allowed(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_2_unauthenticated_user_denied(self):
        self.client.logout()
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_3_authenticated_user_without_organization_forbidden(self):
        self.client.force_authenticate(user=self.no_org_user)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_4_organization_a_accessing_organization_b_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(f"/api/v1/customers/{self.customer_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_5_organization_admin_allowed(self):
        self.client.force_authenticate(user=self.admin_user_a)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_critical_multi_tenant_isolation(self):
        """
        Critical Multi-Tenant Test:
        Verify that user from Organization A sees only Customer A in list queries,
        and receives a 404 error when attempting to fetch Customer B by ID.
        """
        self.client.force_authenticate(user=self.user_a)

        # 1. List query isolation
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        if isinstance(results, dict) and "data" in results:
            results = results["data"]

        customer_names = [item["company_name"] for item in results]
        self.assertIn("Customer A", customer_names)
        self.assertNotIn("Customer B", customer_names)

        # 2. Detail object lookup isolation (404 for cross-tenant ID)
        detail_response = self.client.get(f"/api/v1/customers/{self.customer_b.id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
