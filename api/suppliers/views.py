from rest_framework import status
from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember
from purchases.models import Supplier
from purchases.selectors import SupplierSelector
from purchases.services import SupplierService
from api.suppliers.serializers import SupplierSerializer
from api.utils.responses import success, error
from invoices.views import _get_user_organization


class SupplierViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = SupplierSerializer
    filterset_fields = ["is_active"]
    search_fields = ["company_name", "code", "email", "phone"]
    ordering_fields = ["company_name", "created_at"]
    ordering = ["company_name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return SupplierSelector.list(org)

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        return SupplierService.create_supplier(
            organization=org,
            data=serializer.validated_data
        )

    def perform_update(self, serializer):
        supplier = self.get_object()
        return SupplierService.update_supplier(
            supplier=supplier,
            data=serializer.validated_data
        )
