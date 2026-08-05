from django.test import TestCase
from invoices.models import Organization, Customer
from invoices.services.customer_service import CustomerService

class CustomerServiceTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="ArewaNet Test Org 3", slug="arewanet-test-org-3")

    def test_create_customer(self):
        data = {
            'company_name': 'Kano Digital Tech',
            'contact_person': 'Aminu Bello',
            'email': 'aminu@kanodigital.com',
            'phone': '08099887766',
            'address': 'Farm Centre, Kano'
        }
        customer = CustomerService.create_customer(self.org, data)
        self.assertIsNotNone(customer.pk)
        self.assertEqual(customer.company_name, 'Kano Digital Tech')
        self.assertEqual(customer.organization, self.org)

    def test_get_customer_history(self):
        customer = CustomerService.create_customer(self.org, {'company_name': 'Kaduna Solutions'})
        history = CustomerService.get_customer_history(customer)
        self.assertEqual(history['total_spent'], 0)
        self.assertEqual(history['balance_due'], 0)
