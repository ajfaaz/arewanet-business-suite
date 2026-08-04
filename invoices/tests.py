from django.test import TestCase
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from invoices.forms import InvoiceForm
from invoices.models import Invoice, Customer, Organization, InvoiceItem


class InvoiceFormTest(TestCase):
    def test_invoice_form_init_empty(self):
        try:
            form = InvoiceForm()
        except Exception as e:
            self.fail(f"InvoiceForm initialization failed: {e}")
        self.assertNotIn('customer', form.initial)

    def test_invoice_form_init_with_instance(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        customer = Customer.objects.create(
            organization=org,
            company_name="Test Company",
            email="test@example.com",
            phone="123456",
            address="123 Street"
        )
        invoice = Invoice.objects.create(
            organization=org,
            customer=customer,
            invoice_date=date.today(),
            due_date=date.today(),
            project_name="Test Project",
            deployment_phase="Phase 1",
            status="UNPAID"
        )
        form = InvoiceForm(instance=invoice)
        self.assertEqual(form.instance.customer.company_name, "Test Company")


class InvoiceViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.org = Organization.objects.create(name="ArewaNet Ventures", slug="arewanet-ventures")
        from invoices.models import UserProfile
        UserProfile.objects.create(user=self.user, organization=self.org, role='ADMIN')
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Test Company",
            email="test@example.com",
            phone="123456",
            address="123 Street"
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today(),
            project_name="Test Project",
            deployment_phase="Phase 1",
            status="UNPAID"
        )

    def test_invoice_print_view_without_company_profile(self):
        response = self.client.get(reverse('invoice_print', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ArewaNet Ventures")

    def test_invoice_pdf_view_with_items(self):
        InvoiceItem.objects.create(
            invoice=self.invoice,
            description="Enterprise Deployment\nFull Core Framework",
            qty=1,
            unit_price=1500000.00,
            total=1500000.00
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            description="Technical Support SLA Coverage\n12 Months support",
            qty=1,
            unit_price=0.00,
            total=0.00
        )
        response = self.client.get(reverse('invoice_pdf', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 1000)

    def test_dashboard_view_revenue(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "₦0.00")

        self.invoice.status = 'PAID'
        self.invoice.total_due = 1500000.00
        self.invoice.save()

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "₦1,500,000.00")

    def test_customer_create_assigns_organization(self):
        response = self.client.post(reverse('customer_create'), {
            'company_name': 'New Customer LLC',
            'contact_person': 'Jane Doe',
            'email': 'jane@example.com',
            'phone': '08012345678',
            'address': '456 Commercial Way'
        })
        self.assertEqual(response.status_code, 302)
        new_cust = Customer.objects.get(company_name='New Customer LLC')
        self.assertEqual(new_cust.organization, self.org)

    def test_customer_views(self):
        # Customer detail
        res_detail = self.client.get(reverse('customer_detail', kwargs={'pk': self.customer.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Test Company")

        # Customer history
        res_hist = self.client.get(reverse('customer_history', kwargs={'pk': self.customer.pk}))
        self.assertEqual(res_hist.status_code, 200)
        self.assertContains(res_hist, self.invoice.invoice_no)

        # Customer delete get & post
        res_del_get = self.client.get(reverse('customer_delete', kwargs={'pk': self.customer.pk}))
        self.assertEqual(res_del_get.status_code, 200)

        res_del_post = self.client.post(reverse('customer_delete', kwargs={'pk': self.customer.pk}))
        self.assertEqual(res_del_post.status_code, 302)
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_vat_percentage_calculation(self):
        self.invoice.vat = 7.5
        self.invoice.subtotal = 1000.00
        self.assertEqual(self.invoice.vat_amount, 75.00)

    def test_invoice_create_post_saves_and_calculates_vat(self):
        from decimal import Decimal
        post_data = {
            'customer': self.customer.pk,
            'invoice_date': '2026-08-02',
            'due_date': '2026-09-02',
            'project_name': 'New Web Deployment',
            'deployment_phase': 'Phase 1',
            'status': 'UNPAID',
            'vat': '7.5',
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-description': 'Enterprise Core Framework',
            'items-0-qty': '1',
            'items-0-unit_price': '1000000.00',
            'items-1-description': 'Database Optimization',
            'items-1-qty': '2',
            'items-1-unit_price': '250000.00',
        }
        res = self.client.post(reverse('invoice_create'), post_data)
        self.assertEqual(res.status_code, 302)
        created_inv = Invoice.objects.filter(project_name='New Web Deployment').first()
        self.assertIsNotNone(created_inv)
        self.assertEqual(created_inv.subtotal, Decimal('1500000.00'))
        self.assertEqual(created_inv.vat, Decimal('7.5'))
        self.assertEqual(created_inv.vat_amount, Decimal('112500.00'))
        self.assertEqual(created_inv.total_due, Decimal('1612500.00'))

    def test_invoice_create_post_invalid_form_renders_errors(self):
        res = self.client.post(reverse('invoice_create'), {'vat': '7.5'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Please correct the errors below")

    def test_invoice_list_status_filter(self):
        res_unpaid = self.client.get(reverse('invoice_list') + '?status=unpaid')
        self.assertEqual(res_unpaid.status_code, 200)
        self.assertContains(res_unpaid, self.invoice.invoice_no)

        res_paid = self.client.get(reverse('invoice_list') + '?status=paid')
        self.assertEqual(res_paid.status_code, 200)
        self.assertNotContains(res_paid, self.invoice.invoice_no)

    def test_invoice_duplicate(self):
        res = self.client.get(reverse('invoice_duplicate', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(res.status_code, 302)
        duplicated = Invoice.objects.filter(customer=self.customer).exclude(pk=self.invoice.pk).first()
        self.assertIsNotNone(duplicated)
        self.assertEqual(duplicated.status, 'DRAFT')

    def test_invoice_mark_paid(self):
        res = self.client.get(reverse('invoice_mark_paid', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(res.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'PAID')

    def test_invoice_delete(self):
        res_get = self.client.get(reverse('invoice_delete', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(res_get.status_code, 200)

        res_post = self.client.post(reverse('invoice_delete', kwargs={'pk': self.invoice.pk}))
        self.assertEqual(res_post.status_code, 302)
        self.assertFalse(Invoice.objects.filter(pk=self.invoice.pk).exists())

    def test_payment_workflow_auto_status_and_receipt(self):
        from decimal import Decimal
        from invoices.models import Payment, Receipt

        self.invoice.total_due = Decimal('100000.00')
        self.invoice.status = 'UNPAID'
        self.invoice.save()

        # Step 1: Record partial payment of 40,000
        post_data_1 = {
            'amount': '40000.00',
            'payment_method': 'BANK',
            'payment_date': '2026-08-03',
            'reference': 'TRF-TEST-001',
            'notes': 'First partial payment'
        }
        res1 = self.client.post(reverse('payment_create', kwargs={'invoice_id': self.invoice.pk}), post_data_1)
        self.assertEqual(res1.status_code, 302)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('40000.00'))
        self.assertEqual(self.invoice.balance, Decimal('60000.00'))
        self.assertEqual(self.invoice.status, 'PARTIAL')
        self.assertEqual(self.invoice.payment_percentage, 40.0)

        pay1 = Payment.objects.get(reference='TRF-TEST-001')
        self.assertIsNotNone(pay1.receipt)

        # Step 2: Record remaining payment of 60,000
        post_data_2 = {
            'amount': '60000.00',
            'payment_method': 'POS',
            'payment_date': '2026-08-03',
            'reference': 'POS-TEST-002',
            'notes': 'Final balance settlement'
        }
        res2 = self.client.post(reverse('payment_create', kwargs={'invoice_id': self.invoice.pk}), post_data_2)
        self.assertEqual(res2.status_code, 302)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('100000.00'))
        self.assertEqual(self.invoice.balance, Decimal('0.00'))
        self.assertEqual(self.invoice.status, 'PAID')
        self.assertEqual(self.invoice.payment_percentage, 100.0)

    def test_payment_crud_operations(self):
        from decimal import Decimal
        from invoices.models import Payment, Receipt

        self.invoice.total_due = Decimal('50000.00')
        self.invoice.save()

        # Payment list
        res_list = self.client.get(reverse('payment_list'))
        self.assertEqual(res_list.status_code, 200)

        # Create payment
        res_create = self.client.post(reverse('payment_create', kwargs={'invoice_id': self.invoice.pk}), {
            'amount': '50000.00',
            'payment_method': 'BANK',
            'payment_date': '2026-08-03',
            'reference': 'TRX-CRUD-001',
            'notes': 'Full payment'
        })
        self.assertEqual(res_create.status_code, 302)
        payment = Payment.objects.get(reference='TRX-CRUD-001')

        # Payment detail
        res_detail = self.client.get(reverse('payment_detail', kwargs={'pk': payment.pk}))
        self.assertEqual(res_detail.status_code, 200)

        # Receipt print
        res_rcpt = self.client.get(reverse('receipt_print', kwargs={'pk': payment.receipt.pk}))
        self.assertEqual(res_rcpt.status_code, 200)

        # Update payment
        res_edit = self.client.post(reverse('payment_update', kwargs={'pk': payment.pk}), {
            'amount': '25000.00',
            'payment_method': 'CASH',
            'payment_date': '2026-08-03',
            'reference': 'TRX-CRUD-001',
            'notes': 'Updated partial payment'
        })
        self.assertEqual(res_edit.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'PARTIAL')

        # Delete payment
        res_del = self.client.post(reverse('payment_delete', kwargs={'pk': payment.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'UNPAID')

    def test_overpayment_prevention(self):
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        from invoices.models import Payment

        self.invoice.total_due = Decimal('50000.00')
        self.invoice.save()

        # Attempt to record payment exceeding total_due
        pay = Payment(
            organization=self.invoice.organization,
            invoice=self.invoice,
            reference='TRX-OVERPAY',
            amount=Decimal('70000.00'),
            payment_method='BANK',
            payment_date='2026-08-03'
        )
        with self.assertRaises(ValidationError):
            pay.clean()

    def test_product_and_category_crud_operations(self):
        from invoices.models import ProductCategory, Product

        # 1. Category List & Create
        res_cat_list = self.client.get(reverse('category_list'))
        self.assertEqual(res_cat_list.status_code, 200)

        res_cat_create = self.client.post(reverse('category_create'), {
            'name': 'Software Licensing',
            'description': 'Software items',
            'active': True
        })
        self.assertEqual(res_cat_create.status_code, 302)
        category = ProductCategory.objects.get(name='Software Licensing')
        self.assertEqual(category.organization, self.org)

        # 2. Product List & Create
        res_prod_list = self.client.get(reverse('product_list'))
        self.assertEqual(res_prod_list.status_code, 200)

        res_prod_create = self.client.post(reverse('product_create'), {
            'category': category.pk,
            'product_type': 'SERVICE',
            'name': 'Cloud Hosting Setup',
            'sku': 'SRV-HOST-01',
            'description': 'Annual cloud hosting configuration',
            'unit': 'Year',
            'selling_price': '150000.00',
            'cost_price': '50000.00',
            'minimum_price': '0.00',
            'taxable': True,
            'active': True
        })
        self.assertEqual(res_prod_create.status_code, 302)
        product = Product.objects.get(sku='SRV-HOST-01')
        self.assertEqual(product.organization, self.org)

        # 3. Product Detail
        res_prod_detail = self.client.get(reverse('product_detail', kwargs={'pk': product.pk}))
        self.assertEqual(res_prod_detail.status_code, 200)
        self.assertContains(res_prod_detail, 'Cloud Hosting Setup')

        # 4. Product Update
        res_prod_edit = self.client.post(reverse('product_update', kwargs={'pk': product.pk}), {
            'category': category.pk,
            'product_type': 'SERVICE',
            'name': 'Cloud Hosting Setup Pro',
            'sku': 'SRV-HOST-01',
            'description': 'Updated cloud hosting setup',
            'unit': 'Year',
            'selling_price': '180000.00',
            'cost_price': '60000.00',
            'minimum_price': '0.00',
            'taxable': True,
            'active': True
        })
        self.assertEqual(res_prod_edit.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Cloud Hosting Setup Pro')

        # 5. Product Delete
        res_prod_del = self.client.post(reverse('product_delete', kwargs={'pk': product.pk}))
        self.assertEqual(res_prod_del.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
