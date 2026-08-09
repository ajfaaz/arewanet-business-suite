from rest_framework import status
from rest_framework.decorators import action
from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember
from purchases.models import PurchaseOrder
from purchases.selectors import PurchaseOrderSelector
from purchases.services import PurchaseService
from api.purchases.serializers import (
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseOrderCreateSerializer,
)
from api.utils.responses import success, error
from invoices.views import _get_user_organization


class PurchaseOrderViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    filterset_fields = ["status", "supplier", "warehouse"]
    search_fields = ["order_number", "supplier__company_name"]
    ordering_fields = ["order_date", "total", "created_at"]
    ordering = ["-order_date", "-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return PurchaseOrderSelector.list(org)

    def get_serializer_class(self):
        if self.action == "list":
            return PurchaseOrderListSerializer
        elif self.action == "retrieve":
            return PurchaseOrderDetailSerializer
        return PurchaseOrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = _get_user_organization(request.user)
        vd = serializer.validated_data
        items_data = vd.pop("items", [])

        po = PurchaseService.create_purchase_order(
            organization=org,
            supplier=vd.get("supplier"),
            warehouse=vd.get("warehouse"),
            items_data=items_data,
            order_date=vd.get("order_date"),
            expected_date=vd.get("expected_date"),
            notes=vd.get("notes", ""),
            user=request.user
        )

        detail_serializer = PurchaseOrderDetailSerializer(po)
        return success(data=detail_serializer.data, message="Purchase order created successfully.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        po = self.get_object()
        try:
            po = PurchaseService.submit_purchase_order(po, user=request.user)
            return success(data={"id": po.id, "status": po.status}, message="Purchase order submitted successfully.")
        except Exception as e:
            return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        po = self.get_object()
        try:
            po = PurchaseService.approve_purchase_order(po, user=request.user)
            return success(data={"id": po.id, "status": po.status}, message="Purchase order approved successfully.")
        except Exception as e:
            return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        try:
            po = PurchaseService.cancel_purchase_order(po, user=request.user)
            return success(data={"id": po.id, "status": po.status}, message="Purchase order cancelled successfully.")
        except Exception as e:
            return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        po = self.get_object()
        try:
            po = PurchaseService.close_purchase_order(po, user=request.user)
            return success(data={"id": po.id, "status": po.status}, message="Purchase order closed successfully.")
        except Exception as e:
            return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
