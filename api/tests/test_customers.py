from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Invoice, UserProfile
from sales.models import Quotation

User = get_user_model()


class CustomerAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="custadmin", password="password")
        self.org = Organization.objects.create(name="Customer Test Org", slug="cust-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Arewa Kano Logistics",
            contact_person="Musa Ibrahim",
            email="musa@kanologistics.com",
            phone="08033334444",
            address="Kano State"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_customer(self):
        response = self.client.post("/api/v1/customers/", {
            "company_name": "Kaduna Digital Ltd",
            "contact_person": "Amina Usman",
            "email": "amina@kadunadigital.com",
            "phone": "09077778888",
            "address": "Kaduna State"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["company_name"], "Kaduna Digital Ltd")

    def test_list_customers_and_search(self):
        # List
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Search
        search_res = self.client.get("/api/v1/customers/?search=Kano")
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        self.assertGreater(len(search_res.data["data"]), 0)

    def test_retrieve_customer_detail(self):
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("invoices", response.data["data"])
        self.assertIn("quotations", response.data["data"])

    def test_update_customer(self):
        response = self.client.patch(f"/api/v1/customers/{self.customer.id}/", {
            "contact_person": "Musa Ibrahim Updated"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["contact_person"], "Musa Ibrahim Updated")

    def test_delete_customer(self):
        cust = Customer.objects.create(
            organization=self.org,
            company_name="Temporary Client",
            email="temp@client.com",
            phone="07000000000"
        )
        response = self.client.delete(f"/api/v1/customers/{cust.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Customer.objects.filter(id=cust.id).exists())

    def test_customer_summary(self):
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["customer"], "Arewa Kano Logistics")
        self.assertIn("revenue", response.data["data"])
        self.assertIn("outstanding", response.data["data"])

    def test_customer_timeline(self):
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/timeline/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)

    def test_customer_statement_pdf(self):
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/statement/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_customer_dashboard(self):
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("score", response.data["data"])
        self.assertIn("outstanding", response.data["data"])
