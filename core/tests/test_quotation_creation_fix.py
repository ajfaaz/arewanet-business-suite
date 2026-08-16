from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Customer, Product, Quotation, QuotationItem

User = get_user_model()


class QuotationCreationFixTestCase(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(name="Quote Fix Org", slug="quote-fix-org")
        self.role_admin = Role.objects.get(slug="administrator")

        self.user = User.objects.create_user(username="quote_creator", password="password123")
        self.membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=self.role_admin
        )

        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Acme Corp",
            email="acme@example.com"
        )

        self.product = Product.objects.create(
            organization=self.org,
            name="Consulting Service",
            selling_price=Decimal("150000.00"),
            active=True
        )

    def test_quotation_create_with_product_blank_description_succeeds(self):
        self.client.login(username="quote_creator", password="password123")

        post_data = {
            "customer": self.customer.id,
            "quotation_date": date.today().strftime("%Y-%m-%d"),
            "valid_until": date.today().strftime("%Y-%m-%d"),
            "status": "DRAFT",
            "vat": "7.5",
            "discount": "0.00",
            "notes": "Test notes",
            "terms": "Standard terms",
            # Formset management fields
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Formset row 0 (blank description, product selected)
            "items-0-id": "",
            "items-0-product": self.product.id,
            "items-0-description": "",
            "items-0-qty": "2",
            "items-0-unit_price": "150000.00",
            "items-0-discount": "0.00",
        }

        response = self.client.post(reverse("quotation_create"), post_data)

        # Should redirect to detail view (302)
        self.assertEqual(response.status_code, 302)

        # Verify quotation was saved in DB
        quotation = Quotation.objects.filter(organization=self.org, customer=self.customer).first()
        self.assertIsNotNone(quotation)
        self.assertEqual(quotation.items.count(), 1)

        item = quotation.items.first()
        self.assertEqual(item.product, self.product)
        # Description auto-filled from product name
        self.assertEqual(item.description, "Consulting Service")
