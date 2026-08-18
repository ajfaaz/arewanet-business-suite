from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from invoices.models import Organization, Product, ProductCategory, OrganizationMembership, Role, Permission
from inventory.models import Warehouse
from purchases.models import Supplier, PurchaseOrder

User = get_user_model()


class PurchasingUITestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="purchasing_officer",
            email="purchasing@example.com",
            password="Password123!"
        )
        self.org = Organization.objects.create(name="Global Trade Ltd", slug="global-trade")
        self.role = Role.objects.create(
            name="Purchase Administrator",
            slug="purchase-admin"
        )
        for code in ["supplier.view", "supplier.create", "supplier.edit", "supplier.delete",
                     "purchase_order.view", "purchase_order.create", "purchase_order.edit", "purchase_order.approve"]:
            p = Permission.objects.filter(code=code).first()
            if p:
                self.role.permissions.add(p)

        self.membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=self.role,
            is_active=True
        )

        self.cat = ProductCategory.objects.create(organization=self.org, name="Raw Materials")
        self.product = Product.objects.create(
            organization=self.org,
            category=self.cat,
            name="Steel Beam 10m",
            sku="SB-10M",
            cost_price=Decimal("150000.00"),
            selling_price=Decimal("200000.00"),
            is_stockable=True
        )
        self.warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Central Storage",
            code="WH-CENTRAL"
        )

        self.supplier = Supplier.objects.create(
            organization=self.org,
            code="SUP-000001",
            company_name="Apex Steel Ind Ltd",
            email="apex@steel.com",
            phone="08011112222"
        )

        self.client.login(username="purchasing_officer", password="Password123!")
        session = self.client.session
        session["active_organization_id"] = self.org.id
        session.save()

    def test_supplier_list_view(self):
        response = self.client.get("/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suppliers Directory")
        self.assertContains(response, "Apex Steel Ind Ltd")

    def test_supplier_create_view(self):
        response = self.client.post("/suppliers/create/", {
            "company_name": "Bethel Building Supplies",
            "contact_person": "Grace Okafor",
            "email": "grace@bethel.ng",
            "phone": "08033334444",
            "is_active": True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(company_name="Bethel Building Supplies").exists())

    def test_purchase_order_list_view(self):
        response = self.client.get("/purchases/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Purchase Orders")

    def test_purchase_order_create_view(self):
        response = self.client.post("/purchases/create/", {
            "supplier": self.supplier.pk,
            "warehouse": self.warehouse.pk,
            "order_date": "2026-08-18",
            "notes": "Emergency restock of steel beams",
            "product_id[]": [self.product.pk],
            "quantity[]": ["5.00"],
            "unit_cost[]": ["140000.00"],
        })
        self.assertEqual(response.status_code, 302)
        po = PurchaseOrder.objects.filter(supplier=self.supplier).first()
        self.assertIsNotNone(po)
        self.assertEqual(po.subtotal, Decimal("700000.00"))

    def test_sidebar_renders_active_purchasing_menu(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suppliers")
        self.assertContains(response, "Purchase Orders")
        # Ensure (Soon) is no longer rendered for Purchasing items
        self.assertNotContains(response, 'Suppliers <small class="text-xs ms-1">(Soon)</small>')
