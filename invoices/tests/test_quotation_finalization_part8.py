from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

from invoices.models import (
    Organization, Customer, Product, Quotation, QuotationItem, QuotationTemplate, OrganizationMembership, Role, UserProfile
)
from core.choices import QuotationStatus
from invoices.services.quotation_finalization_service import QuotationFinalizationService
from sales.services.quotation_service import QuotationService

User = get_user_model()


class QuotationFinalizationGovernanceTestCase(TestCase):

    def setUp(self):
        # Create Organization A
        self.org_a = Organization.objects.create(
            name="Org Alpha",
            slug="org-alpha"
        )
        self.user_a = User.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password="password123"
        )
        self.user_a.organization = self.org_a
        UserProfile.objects.create(user=self.user_a, organization=self.org_a, role="ADMIN")
        self.role_admin, _ = Role.objects.get_or_create(
            slug="administrator",
            defaults={"name": "Administrator"}
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=self.role_admin,
            is_active=True
        )

        # Create Organization B
        self.org_b = Organization.objects.create(
            name="Org Beta",
            slug="org-beta"
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="user_b@example.com",
            password="password123"
        )
        self.user_b.organization = self.org_b
        UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="ADMIN")
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=self.role_admin,
            is_active=True
        )

        # Customers
        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            company_name="Customer Alpha Ltd",
            email="alpha@cust.com",
            phone="08011111111",
            address="1 Alpha Way"
        )
        self.customer_b = Customer.objects.create(
            organization=self.org_b,
            company_name="Customer Beta Ltd",
            email="beta@cust.com",
            phone="08022222222",
            address="2 Beta Way"
        )

        # Products
        self.product_a = Product.objects.create(
            organization=self.org_a,
            name="Alpha Service",
            selling_price=Decimal("10000.00"),
            unit="Service"
        )

        # Templates
        self.template_modern = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Modern Template A",
            style="modern",
            is_active=True,
            is_default=True
        )
        self.template_classic = QuotationTemplate.objects.create(
            organization=self.org_a,
            name="Classic Template A",
            style="classic",
            is_active=True,
            is_default=False
        )

        # Draft Quotation
        self.draft_quotation = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            template=self.template_modern,
            quotation_date=date.today(),
            status=QuotationStatus.DRAFT
        )
        self.item_1 = QuotationItem.objects.create(
            quotation=self.draft_quotation,
            product=self.product_a,
            description="Item 1 Description",
            qty=Decimal("2.00"),
            unit_price=Decimal("10000.00"),
            total=Decimal("20000.00")
        )
        self.draft_quotation.subtotal = Decimal("20000.00")
        self.draft_quotation.total = Decimal("20000.00")
        self.draft_quotation.save()

        # Web Client
        self.client_a = Client()
        self.client_a.login(username="user_a", password="password123")

        self.client_b = Client()
        self.client_b.login(username="user_b", password="password123")

        # API Client
        self.api_client_a = APIClient()
        self.api_client_a.force_authenticate(user=self.user_a)

        self.api_client_b = APIClient()
        self.api_client_b.force_authenticate(user=self.user_b)

    def test_draft_can_be_edited_and_template_changed(self):
        """Test that a Draft quotation can change template and line items."""
        self.assertEqual(self.draft_quotation.status, QuotationStatus.DRAFT)
        
        # Change template to Classic
        self.item_1.qty = Decimal("3.00")
        self.item_1.save()

        updated = QuotationService.update(
            self.draft_quotation,
            [self.item_1],
            user=self.user_a
        )
        updated.template = self.template_classic
        updated.save()

        self.assertEqual(updated.template, self.template_classic)
        self.assertEqual(updated.total, Decimal("30000.00"))

    def test_finalization_locks_document_and_populates_fields(self):
        """Test that finalizing populates issued_at, issued_by, and status SENT."""
        finalized = QuotationFinalizationService.finalize(
            self.draft_quotation,
            user=self.user_a,
            target_status=QuotationStatus.SENT
        )

        self.assertEqual(finalized.status, QuotationStatus.SENT)
        self.assertIsNotNone(finalized.issued_at)
        self.assertEqual(finalized.issued_by, self.user_a)

    def test_zero_item_quotation_finalization_fails(self):
        """Test that attempting to finalize a quotation with 0 items raises a ValidationError."""
        empty_quotation = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            template=self.template_modern,
            quotation_date=date.today(),
            status=QuotationStatus.DRAFT
        )
        with self.assertRaises(ValidationError) as ctx:
            QuotationFinalizationService.finalize(empty_quotation, user=self.user_a)
        self.assertIn("at least one item", str(ctx.exception))

    def test_invalid_item_qty_or_price_finalization_fails(self):
        """Test that zero quantity or negative price fails finalization."""
        bad_quotation = Quotation.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            template=self.template_modern,
            quotation_date=date.today(),
            status=QuotationStatus.DRAFT
        )
        QuotationItem.objects.create(
            quotation=bad_quotation,
            description="Bad Item",
            qty=Decimal("0.00"),
            unit_price=Decimal("100.00"),
            total=Decimal("0.00")
        )
        with self.assertRaises(ValidationError) as ctx:
            QuotationFinalizationService.finalize(bad_quotation, user=self.user_a)
        self.assertIn("greater than zero", str(ctx.exception))

    def test_issued_quotation_cannot_be_edited_via_service(self):
        """Test that QuotationService.update rejects modifications on an issued quotation."""
        finalized = QuotationFinalizationService.finalize(
            self.draft_quotation,
            user=self.user_a
        )
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.update(finalized, [self.item_1], user=self.user_a)
        self.assertIn("finalized", str(ctx.exception))

    def test_issued_quotation_cannot_be_edited_via_web_view(self):
        """Test web view /quotation/<id>/edit/ blocks editing an issued quotation."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        response = self.client_a.get(f"/quotation/{self.draft_quotation.pk}/edit/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/quotation/{self.draft_quotation.pk}/", response.url)

    def test_issued_quotation_cannot_be_deleted_via_web_view(self):
        """Test web view /quotation/<id>/delete/ blocks deleting an issued quotation."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        response = self.client_a.post(f"/quotation/{self.draft_quotation.pk}/delete/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Quotation.objects.filter(pk=self.draft_quotation.pk).exists())

    def test_issued_quotation_cannot_be_edited_via_api(self):
        """Test REST API PATCH on an issued quotation returns 400 Bad Request."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        url = f"/api/v1/quotations/{self.draft_quotation.pk}/"
        response = self.api_client_a.patch(
            url,
            data={"template": self.template_classic.id},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("finalized", str(response.content))

    def test_issued_quotation_status_downgrade_rejected_via_api(self):
        """Test REST API PATCH trying to set status back to DRAFT is rejected."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        url = f"/api/v1/quotations/{self.draft_quotation.pk}/"
        response = self.api_client_a.patch(
            url,
            data={"status": "DRAFT"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_issued_quotation_cannot_be_deleted_via_api(self):
        """Test REST API DELETE on an issued quotation returns 400 Bad Request."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        url = f"/api/v1/quotations/{self.draft_quotation.pk}/"
        response = self.api_client_a.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Quotation.objects.filter(pk=self.draft_quotation.pk).exists())

    def test_api_issue_action_endpoint(self):
        """Test POST /api/v1/quotations/<id>/issue/ endpoint officially issues quotation."""
        url = f"/api/v1/quotations/{self.draft_quotation.pk}/issue/"
        response = self.api_client_a.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.draft_quotation.refresh_from_db()
        self.assertEqual(self.draft_quotation.status, QuotationStatus.SENT)
        self.assertIsNotNone(self.draft_quotation.issued_at)

    def test_deactivated_template_renders_for_existing_quotation(self):
        """Test that deactivating a template bound to an issued quotation still allows preview and PDF rendering."""
        QuotationFinalizationService.finalize(self.draft_quotation, user=self.user_a)

        # Deactivate Modern Template
        self.template_modern.is_active = False
        self.template_modern.save()

        # Preview view
        preview_url = f"/quotation-templates/0/preview/?quotation={self.draft_quotation.pk}"
        response_prev = self.client_a.get(preview_url)
        self.assertEqual(response_prev.status_code, 200)

        # PDF view
        pdf_url = f"/quotation/{self.draft_quotation.pk}/pdf/"
        response_pdf = self.client_a.get(pdf_url)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf["Content-Type"], "application/pdf")
        self.assertIn(f"Quotation-{self.draft_quotation.quotation_no}.pdf", response_pdf["Content-Disposition"])

    def test_deactivated_template_cannot_be_selected_for_new_quotation(self):
        """Test that a deactivated template is rejected when submitting a new quotation form."""
        self.template_classic.is_active = False
        self.template_classic.save()

        form_data = {
            "customer": self.customer_a.id,
            "template": self.template_classic.id,
            "quotation_date": "2026-08-18",
            "status": "DRAFT",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-description": "New Item",
            "items-0-qty": "1",
            "items-0-unit_price": "5000",
        }
        response = self.client_a.post("/quotation/create/", form_data)
        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertIn("is not one of the available choices", str(response.content))

    def test_multi_organization_isolation(self):
        """Test that User B from Org B cannot access or issue Org A's quotation."""
        url_issue = f"/quotation/{self.draft_quotation.pk}/issue/"
        response = self.client_b.post(url_issue)
        self.assertEqual(response.status_code, 404)

        url_api = f"/api/v1/quotations/{self.draft_quotation.pk}/issue/"
        response_api = self.api_client_b.post(url_api)
        self.assertEqual(response_api.status_code, status.HTTP_404_NOT_FOUND)

    def test_template_deletion_protected(self):
        """Test that template bound to a quotation cannot be deleted due to PROTECT foreign key."""
        with self.assertRaises(ProtectedError):
            self.template_modern.delete()
