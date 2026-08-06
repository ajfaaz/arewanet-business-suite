from decimal import Decimal
from datetime import date
from django.test import TestCase
from invoices.models import Organization, Customer, Product, Invoice, Payment
from sales.models import Quotation, QuotationItem
from sales.services.dashboard_service import DashboardService
from sales.services.search_service import SearchService
from sales.services.quotation_service import QuotationService

class SalesEngineServicesTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Sales Engine Org", slug="sales-engine-org")
        self.customer = Customer.objects.create(
            organization=self.org,
            company_name="Northern Trade Ltd",
            email="info@northerntrade.com"
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="ERP Hosting Package",
            sku="ERP-HOST-01",
            selling_price=Decimal("250000.00")
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_date=date.today(),
            due_date=date.today(),
            project_name="ERP System Setup",
            subtotal=Decimal("250000.00"),
            total_due=Decimal("250000.00"),
            status="UNPAID"
        )

    def test_dashboard_service_statistics(self):
        stats = DashboardService.statistics(organization=self.org)
        self.assertEqual(stats['total_customers'], 1)
        self.assertEqual(stats['total_products'], 1)
        self.assertEqual(stats['total_invoices'], 1)
        self.assertEqual(stats['outstanding_balance'], Decimal("250000.00"))

    def test_global_search_service(self):
        res = SearchService.global_search("ERP", organization=self.org)
        self.assertTrue(len(res['invoices']) > 0 or len(res['products']) > 0)
        self.assertEqual(res['total_results'], len(res['invoices']) + len(res['products']))

    def test_quotation_creation_and_conversion(self):
        qtn = Quotation(
            organization=self.org,
            customer=self.customer,
            document_number="QTN-2026-0001",
            issue_date=date.today(),
            due_date=date.today(),
            notes="Quotation for ERP deployment"
        )
        item = QuotationItem(description="ERP Installation", quantity=1, unit_price=Decimal("300000.00"))
        created_qtn = QuotationService.create_quotation(qtn, [item])
        self.assertEqual(created_qtn.total_amount, Decimal("300000.00"))

        inv = QuotationService.convert_to_invoice(created_qtn)
        self.assertIsNotNone(inv.pk)
        self.assertEqual(inv.total_due, Decimal("300000.00"))
        self.assertEqual(created_qtn.status, "APPROVED")
