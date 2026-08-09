from purchases.models import Supplier, PurchaseOrder


class SupplierSelector:

    @staticmethod
    def list(organization):
        return Supplier.objects.filter(organization=organization)

    @staticmethod
    def get_by_id(organization, supplier_id):
        return Supplier.objects.filter(organization=organization, pk=supplier_id).first()


class PurchaseOrderSelector:

    @staticmethod
    def list(organization):
        return PurchaseOrder.objects.filter(organization=organization).select_related("supplier", "warehouse").prefetch_related("items__product")

    @staticmethod
    def get_by_id(organization, po_id):
        return PurchaseOrder.objects.filter(organization=organization, pk=po_id).select_related("supplier", "warehouse").prefetch_related("items__product").first()
