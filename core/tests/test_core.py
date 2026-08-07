from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from core.services.base import BaseService
from core.selectors.base import BaseSelector
from core.constants import InvoiceStatus, PaymentMethod, PaymentStatus, QuotationStatus, SubscriptionStatus
from core.exceptions import CustomerNotFound, InvoiceNotFound, InsufficientBalanceException
from core.permissions import can_create_invoice, can_delete_invoice, can_view_reports, can_manage_customers
from core.logger import log_activity, log_event
from core.settings import VAT_RATE, DEFAULT_CURRENCY
from invoices.models import Organization, Customer, UserProfile, ActivityLog

User = get_user_model()


class CoreFrameworkTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="coreadmin", password="password")
        self.org = Organization.objects.create(name="Core Framework Org", slug="core-fw-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")

    def test_base_service_crud(self):
        customer = BaseService.create(
            Customer,
            organization=self.org,
            company_name="Core Test Customer",
            email="core@test.com"
        )
        self.assertIsNotNone(customer.id)
        self.assertEqual(customer.company_name, "Core Test Customer")

        updated_customer = BaseService.update(customer, company_name="Core Updated Customer")
        self.assertEqual(updated_customer.company_name, "Core Updated Customer")

        BaseService.delete(customer)
        self.assertFalse(Customer.objects.filter(id=customer.id).exists())

    def test_base_selector(self):
        customer = Customer.objects.create(
            organization=self.org,
            company_name="Selector Test Customer",
            email="selector@test.com"
        )
        qs = BaseSelector.list(Customer.objects.filter(organization=self.org))
        self.assertEqual(qs.count(), 1)

        fetched = BaseSelector.get(Customer, id=customer.id)
        self.assertEqual(fetched.id, customer.id)

    def test_permissions(self):
        self.assertTrue(can_create_invoice(self.user))
        self.assertTrue(can_delete_invoice(self.user))
        self.assertTrue(can_view_reports(self.user))
        self.assertTrue(can_manage_customers(self.user))

    def test_exceptions(self):
        exc = CustomerNotFound("Customer missing")
        self.assertEqual(str(exc), "Customer missing")

        bal_exc = InsufficientBalanceException()
        self.assertEqual(str(bal_exc), "Payment amount exceeds outstanding invoice balance.")

    def test_constants_and_settings(self):
        self.assertEqual(InvoiceStatus.PAID, "PAID")
        self.assertEqual(PaymentStatus.COMPLETED, "COMPLETED")
        self.assertEqual(PaymentMethod.BANK, "BANK")
        self.assertEqual(QuotationStatus.APPROVED, "APPROVED")
        self.assertEqual(SubscriptionStatus.ACTIVE, "ACTIVE")
        self.assertEqual(VAT_RATE, Decimal("7.5"))
        self.assertEqual(DEFAULT_CURRENCY, "NGN")

    def test_logger(self):
        log_activity(self.user, "Core framework test activity")
        self.assertTrue(ActivityLog.objects.filter(action="Core framework test activity").exists())

        log_event("info", "System initialized successfully")
