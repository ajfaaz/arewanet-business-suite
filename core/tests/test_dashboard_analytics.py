from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from invoices.models import Organization, OrganizationMembership, Role, Permission, Customer, Invoice, Quotation, Product
from invoices.services.dashboard_service import DashboardService

User = get_user_model()


class DashboardAnalyticsTestCase(TestCase):

    def setUp(self):
        # Retrieve system roles
        self.role_admin = Role.objects.get(slug="administrator")
        self.role_sales = Role.objects.get(slug="sales-officer")

        # Create organizations
        self.org_a = Organization.objects.create(name="Analytics Org A", slug="analytics-org-a")
        self.org_b = Organization.objects.create(name="Analytics Org B", slug="analytics-org-b")

        # Create user
        self.user = User.objects.create_user(username="analyticsuser", password="password123")
        self.m_a = OrganizationMembership.objects.create(user=self.user, organization=self.org_a, role=self.role_admin)
        self.m_b = OrganizationMembership.objects.create(user=self.user, organization=self.org_b, role=self.role_sales)

        # Org A Invoices
        c_a = Customer.objects.create(company_name="Client A", organization=self.org_a)
        Invoice.objects.create(
            invoice_no="INV-A-1",
            customer=c_a,
            organization=self.org_a,
            invoice_date=date.today(),
            due_date=date.today() - timedelta(days=10),
            subtotal=Decimal("10000000.00"),
            total_due=Decimal("10000000.00"),
            status="UNPAID"
        )

        # Org B Invoices
        c_b = Customer.objects.create(company_name="Client B", organization=self.org_b)
        Invoice.objects.create(
            invoice_no="INV-B-1",
            customer=c_b,
            organization=self.org_b,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=15),
            subtotal=Decimal("50000000.00"),
            total_due=Decimal("50000000.00"),
            status="UNPAID"
        )

        # Org A Product with Low Stock
        Product.objects.create(
            name="Laptop A",
            organization=self.org_a,
            reorder_level=Decimal("10.00"),
            cost_price=Decimal("150000.00"),
            selling_price=Decimal("200000.00"),
            is_stockable=True
        )

        # Org B Product with Low Stock
        Product.objects.create(
            name="Printer B",
            organization=self.org_b,
            reorder_level=Decimal("5.00"),
            cost_price=Decimal("50000.00"),
            selling_price=Decimal("75000.00"),
            is_stockable=True
        )

    def test_sales_trend_multi_tenant_isolation(self):
        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        trend_a = service_a.get_sales_trend(period='month')
        trend_b = service_b.get_sales_trend(period='month')

        self.assertEqual(len(trend_a), 1)
        self.assertEqual(trend_a[0]['amount_raw'], 10000000.0)

        self.assertEqual(len(trend_b), 1)
        self.assertEqual(trend_b[0]['amount_raw'], 50000000.0)

    def test_date_range_filtering(self):
        # Create an invoice in previous month for Org A
        old_date = date.today().replace(day=1) - timedelta(days=40)
        c_a = Customer.objects.filter(organization=self.org_a).first()
        Invoice.objects.create(
            invoice_no="INV-A-OLD",
            customer=c_a,
            organization=self.org_a,
            invoice_date=old_date,
            due_date=old_date,
            subtotal=Decimal("500000.00"),
            total_due=Decimal("500000.00"),
            status="UNPAID"
        )

        service_a = DashboardService(self.org_a)
        trend_month = service_a.get_sales_trend(period='month')

        # Previous month invoice should be excluded from 'month' period trend
        total_in_trend = sum(t['amount_raw'] for t in trend_month)
        self.assertEqual(total_in_trend, 10000000.0)

    def test_low_stock_tenant_isolation(self):
        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        items_a = service_a.get_low_stock_items()
        items_b = service_b.get_low_stock_items()

        self.assertEqual(len(items_a), 1)
        self.assertEqual(items_a[0]['name'], "Laptop A")

        self.assertEqual(len(items_b), 1)
        self.assertEqual(items_b[0]['name'], "Printer B")

    def test_pending_approvals_tenant_isolation(self):
        Quotation.objects.create(
            quotation_no="QT-A-1",
            customer=Customer.objects.filter(organization=self.org_a).first(),
            organization=self.org_a,
            status="DRAFT",
            subtotal=Decimal("100.00"),
            total=Decimal("100.00")
        )

        service_a = DashboardService(self.org_a)
        service_b = DashboardService(self.org_b)

        pending_a = service_a.get_pending_approvals()
        pending_b = service_b.get_pending_approvals()

        self.assertEqual(pending_a['quotations'], 1)
        self.assertEqual(pending_b['quotations'], 0)

    def test_permission_restricted_analytics(self):
        user_restricted = User.objects.create_user(username="restricteduser", password="password123")
        custom_role = Role.objects.create(name="Restricted Role", slug="restricted-role", is_active=True)
        m_restricted = OrganizationMembership.objects.create(user=user_restricted, organization=self.org_a, role=custom_role)

        service = DashboardService(self.org_a)
        trend = service.get_sales_trend(membership=m_restricted)
        receivables = service.get_outstanding_receivables(membership=m_restricted)

        self.assertEqual(trend, [])
        self.assertIsNone(receivables)

    def test_recent_activity_normalized_timeline(self):
        service_a = DashboardService(self.org_a)
        timeline = service_a.get_normalized_activity_timeline()

        self.assertGreaterEqual(len(timeline), 1)
        self.assertEqual(timeline[0]['reference'], "INV-A-1")
