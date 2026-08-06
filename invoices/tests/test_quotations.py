from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from invoices.models import Organization, Customer, Product, Invoice, Quotation, QuotationItem
from sales.services.quotation_service import QuotationService

class QuotationModuleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='quoteuser', password='password')
        self.client.login(username='quoteuser', password='password')
        self.org = Organization.objects.create(name="Quotation Test Org", slug="quotation-test-org")
        from invoices.models import UserProfile
        UserProfile.objects.create(user=self.user, organization=self.org, role='ADMIN')

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Delta Systems Ltd",
            email="delta@example.com"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Network Setup Service",
            sku="NET-SETUP-01",
            selling_price=Decimal("150000.00")
        )

    def test_quotation_crud_and_conversion_workflow(self):
        # 1. Quotation List GET
        res_list = self.client.get(reverse('quotation_list'))
        self.assertEqual(res_list.status_code, 200)

        # 2. Quotation Create POST
        res_create = self.client.post(reverse('quotation_create'), {
            'customer': self.customer.pk,
            'quotation_date': '2026-08-05',
            'valid_until': '2026-08-25',
            'status': 'DRAFT',
            'vat': '7.50',
            'discount': '10000.00',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.pk,
            'items-0-description': 'Network Installation & Setup',
            'items-0-qty': '2',
            'items-0-unit_price': '150000.00',
            'items-0-discount': '0.00'
        })
        self.assertEqual(res_create.status_code, 302)
        qtn = Quotation.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(qtn)
        self.assertEqual(qtn.subtotal, Decimal("300000.00"))

        # 3. Quotation Detail GET
        res_detail = self.client.get(reverse('quotation_detail', kwargs={'pk': qtn.pk}))
        self.assertEqual(res_detail.status_code, 200)

        # 4. Quotation Print GET
        res_print = self.client.get(reverse('quotation_print', kwargs={'pk': qtn.pk}))
        self.assertEqual(res_print.status_code, 200)
        self.assertContains(res_print, "QUOTATION")

        # 5. Quotation Convert to Invoice
        res_convert = self.client.get(reverse('quotation_convert', kwargs={'pk': qtn.pk}))
        self.assertEqual(res_convert.status_code, 302)
        qtn.refresh_from_db()
        self.assertEqual(qtn.status, 'CONVERTED')

        inv = Invoice.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(inv)
        self.assertEqual(inv.items.count(), 1)

    def test_quotation_delete(self):
        qtn = Quotation.objects.create(
            organization=self.org,
            customer=self.customer,
            quotation_date=date.today(),
            total=Decimal("50000.00")
        )
        res_del = self.client.post(reverse('quotation_delete', kwargs={'pk': qtn.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Quotation.objects.filter(pk=qtn.pk).exists())
