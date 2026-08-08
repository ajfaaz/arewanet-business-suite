from django.test import TestCase
from django.db import transaction
from django.db.utils import IntegrityError
from invoices.models import Organization
from inventory.models import Warehouse, WarehouseLocation
from inventory.selectors import WarehouseSelector, WarehouseLocationSelector


class WarehouseModelTestCase(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(name="ArewaNet Logistics", slug="arewanet-logistics")
        self.org_b = Organization.objects.create(name="Sahara Retail Ltd", slug="sahara-retail")

    def test_warehouse_creation_and_unique_code_per_org(self):
        wh_a1 = Warehouse.objects.create(
            organization=self.org_a,
            name="Kano Central Depot",
            code="MAIN",
            address="Commercial Layout, Kano"
        )
        self.assertEqual(str(wh_a1), "Kano Central Depot (MAIN)")

        # Same code "MAIN" in a DIFFERENT organization should be allowed
        wh_b1 = Warehouse.objects.create(
            organization=self.org_b,
            name="Abuja Main Hub",
            code="MAIN",
            address="Central Business District, Abuja"
        )
        self.assertEqual(wh_b1.code, "MAIN")

        # Duplicate code "MAIN" in SAME organization should raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Warehouse.objects.create(
                    organization=self.org_a,
                    name="Duplicate Kano Depot",
                    code="MAIN"
                )

    def test_warehouse_organization_isolation(self):
        wh_a = Warehouse.objects.create(organization=self.org_a, name="Kano Main", code="WH-KNO")
        wh_b = Warehouse.objects.create(organization=self.org_b, name="Lagos Port Hub", code="WH-LOS")

        # Querying org_a warehouses should only return org_a warehouse
        wh_list_a = WarehouseSelector.list(organization=self.org_a)
        self.assertIn(wh_a, wh_list_a)
        self.assertNotIn(wh_b, wh_list_a)

        # get_by_id cross-tenant security check
        self.assertIsNone(WarehouseSelector.get_by_id(organization=self.org_a, warehouse_id=wh_b.id))

    def test_warehouse_location_creation_and_constraints(self):
        wh = Warehouse.objects.create(organization=self.org_a, name="Kaduna Store", code="WH-KDA")

        loc_1 = WarehouseLocation.objects.create(warehouse=wh, name="Store Room A", code="LOC-A")
        loc_2 = WarehouseLocation.objects.create(warehouse=wh, name="Store Room B", code="LOC-B")

        self.assertEqual(str(loc_1), "WH-KDA - Store Room A (LOC-A)")

        # Duplicate location code in SAME warehouse raises IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WarehouseLocation.objects.create(warehouse=wh, name="Duplicate Store A", code="LOC-A")

        locations = WarehouseLocationSelector.list(warehouse=wh)
        self.assertEqual(locations.count(), 2)
