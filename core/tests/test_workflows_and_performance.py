from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Product, Quotation, Invoice, UserProfile
from sales.payments.models import Payment

User = get_user_model()


class WorkflowsAndPerformanceTestCase(TestCase):

    def setUp(self):
        # Organization A setup
        self.org_a = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet-ventures")
        self.user_a = User.objects.create_user(username="workflowusera", password="password123")
        self.profile_a = UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")

        # Organization B setup
        self.org_b = Organization.objects.create(name="ABC Tech", slug="abc-tech")
        self.user_b = User.objects.create_user(username="workflowuserb", password="password123")
        self.profile_b = UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")

        self.client = APIClient()

    def test_health_check_endpoint(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], "ok")

    def test_workflow_quotation_to_invoice_conversion(self):
        self.client.force_authenticate(user=self.user_a)

        # 1. Create Customer
        cust_resp = self.client.post("/api/v1/customers/", {
            "company_name": "Enterprise Client Ltd",
            "contact_person": "Aliyu Musa",
            "phone": "+2348030000000",
            "address": "Plot 12, Commercial Layout, Kano",
            "email": "client@enterprise.com"
        }, format="json")
        self.assertEqual(cust_resp.status_code, status.HTTP_201_CREATED)
        customer_id = cust_resp.data["data"]["id"]

        # 2. Create Product
        prod_resp = self.client.post("/api/v1/products/", {
            "name": "Cloud ERP License",
            "selling_price": "500000.00"
        }, format="json")
        self.assertEqual(prod_resp.status_code, status.HTTP_201_CREATED)

        # 3. Create Quotation
        qtn_resp = self.client.post("/api/v1/quotations/", {
            "customer": customer_id,
            "items": [
                {"description": "Cloud License", "qty": 1, "unit_price": "500000.00"}
            ]
        }, format="json")
        self.assertEqual(qtn_resp.status_code, status.HTTP_201_CREATED)
        quotation_id = qtn_resp.data["data"]["id"]

        # 4. Convert Quotation to Invoice
        conv_resp = self.client.post(f"/api/v1/quotations/{quotation_id}/convert/")
        self.assertEqual(conv_resp.status_code, status.HTTP_200_OK)
        self.assertIn("invoice_no", conv_resp.data["data"])
        invoice_no = conv_resp.data["data"]["invoice_no"]
        self.assertTrue(invoice_no.startswith("ANV-"))

    def test_workflow_invoice_to_payment_to_receipt(self):
        self.client.force_authenticate(user=self.user_a)

        # 1. Create Customer
        customer = Customer.objects.create(organization=self.org_a, company_name="Payment Client Ltd", email="pmt@client.com")

        # 2. Create Invoice
        invoice = Invoice.objects.create(
            organization=self.org_a,
            customer=customer,
            invoice_no="INV-2026-FLOW1",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal("200000.00"),
            total_due=Decimal("200000.00"),
            status="UNPAID"
        )

        # 3. Receive Payment
        pmt_resp = self.client.post("/api/v1/payments/", {
            "invoice": invoice.id,
            "customer": customer.id,
            "amount": "200000.00",
            "payment_method": "BANK"
        }, format="json")
        self.assertEqual(pmt_resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("receipt_number", pmt_resp.data["data"])

        # 4. Verify Invoice status updated to PAID
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "PAID")
        self.assertEqual(invoice.balance_due, Decimal("0.00"))

    def test_multi_tenant_boundary_workflow(self):
        # Create Customer in Org B
        customer_b = Customer.objects.create(organization=self.org_b, company_name="Secret Org B Customer", email="secret@orgb.com")

        # Authenticate as Org A user
        self.client.force_authenticate(user=self.user_a)

        # Org A cannot access Org B customer
        response = self.client.get(f"/api/v1/customers/{customer_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_count_invoices_list(self):
        self.client.force_authenticate(user=self.user_a)
        customer = Customer.objects.create(organization=self.org_a, company_name="Query Customer", email="query@cust.com")
        for i in range(5):
            Invoice.objects.create(
                organization=self.org_a,
                customer=customer,
                invoice_no=f"INV-Q-{i}",
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                subtotal=Decimal("1000.00"),
                total_due=Decimal("1000.00")
            )

        with self.assertNumQueries(45):
            response = self.client.get("/api/v1/invoices/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
