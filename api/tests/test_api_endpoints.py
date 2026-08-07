from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, Customer, Product, Invoice, InvoiceItem
from sales.subscriptions.models import Subscription, SubscriptionItem
from core.choices import SubscriptionStatus, BillingCycle

User = get_user_model()


class EnterpriseAPITest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="apiadmin", password="apipassword")
        self.org = Organization.objects.create(name="ArewaNet API Org", slug="arewanet-api-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Apex Global Ltd",
            email="apex@global.com",
            phone="08011223344"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Cloud Server",
            selling_price=Decimal("150000.00")
        )
        self.client = APIClient()

    def test_jwt_auth_and_profile(self):
        # 1. Login
        res = self.client.post('/api/v1/auth/login/', {
            'username': 'apiadmin',
            'password': 'apipassword'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['data'])
        access_token = res.data['data']['access']

        # 2. Access /api/v1/auth/me/ with Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_res = self.client.get('/api/v1/auth/me/')
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data['data']['username'], 'apiadmin')

    def test_customer_api_and_summary(self):
        self.client.force_authenticate(user=self.user)

        # Create Customer
        res = self.client.post('/api/v1/customers/', {
            'company_name': 'TechCorp Ltd',
            'email': 'tech@corp.com',
            'phone': '09088776655',
            'address': 'Kano, Nigeria'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cust_id = res.data['data']['id']

        # List Customers
        list_res = self.client.get('/api/v1/customers/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)

        # Customer Summary
        summary_res = self.client.get(f'/api/v1/customers/{cust_id}/summary/')
        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_res.data['data']['customer'], 'TechCorp Ltd')

    def test_product_api(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/v1/products/', {
            'name': 'Managed Security',
            'selling_price': '250000.00',
            'product_type': 'SERVICE'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_quotation_creation_and_conversion_api(self):
        self.client.force_authenticate(user=self.user)
        qtn_res = self.client.post('/api/v1/quotations/', {
            'customer': self.customer.id,
            'quotation_date': str(date.today()),
            'valid_until': str(date.today() + timedelta(days=14)),
            'items': [
                {'description': 'Enterprise ERP Setup', 'qty': '1', 'unit_price': '500000.00'}
            ]
        }, format='json')
        self.assertEqual(qtn_res.status_code, status.HTTP_201_CREATED)
        qtn_id = qtn_res.data['data']['id']

        # Convert quotation to invoice
        convert_res = self.client.post(f'/api/v1/quotations/{qtn_id}/convert/')
        self.assertEqual(convert_res.status_code, status.HTTP_200_OK)
        self.assertTrue(convert_res.data['data']['invoice_no'].startswith('ANV') or convert_res.data['data']['invoice_no'].startswith('INV'))

    def test_invoice_creation_and_payment_api(self):
        self.client.force_authenticate(user=self.user)

        inv = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-2026-9001",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal("100000.00"),
            total_due=Decimal("100000.00"),
            status="UNPAID"
        )

        pay_res = self.client.post(f'/api/v1/invoices/{inv.id}/pay/', {
            'amount': '50000.00',
            'payment_method': 'BANK',
            'reference': 'TRX-PAY-9001'
        })
        self.assertEqual(pay_res.status_code, status.HTTP_200_OK)
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'PARTIAL')

    def test_subscription_lifecycle_api(self):
        self.client.force_authenticate(user=self.user)

        sub_res = self.client.post('/api/v1/subscriptions/', {
            'title': 'Monthly SLA Support',
            'customer': self.customer.id,
            'start_date': str(date.today()),
            'billing_cycle': 'MONTHLY',
            'items': [
                {'description': 'ICT Helpdesk', 'qty': '1', 'unit_price': '75000.00'}
            ]
        }, format='json')
        self.assertEqual(sub_res.status_code, status.HTTP_201_CREATED)
        sub_id = sub_res.data['data']['id']

        # Pause
        pause_res = self.client.post(f'/api/v1/subscriptions/{sub_id}/pause/')
        self.assertEqual(pause_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pause_res.data['data']['status'], 'PAUSED')

        # Resume
        resume_res = self.client.post(f'/api/v1/subscriptions/{sub_id}/resume/')
        self.assertEqual(resume_res.status_code, status.HTTP_200_OK)
        self.assertEqual(resume_res.data['data']['status'], 'ACTIVE')

    def test_dashboard_api(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/v1/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('revenue', res.data['data'])
        self.assertIn('outstanding', res.data['data'])
        self.assertIn('mrr', res.data['data'])

    def test_openapi_schema_endpoint(self):
        res = self.client.get('/api/schema/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
