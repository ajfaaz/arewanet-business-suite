from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from invoices.views import _get_user_organization
from invoices.models import Product
from inventory.models import StockMovement, Warehouse
from inventory.selectors import StockLedgerSelector
from inventory.serializers import StockLedgerMovementSerializer
from inventory.pagination import InventoryLedgerPagination


class StockLedgerAPIView(generics.ListAPIView):
    """
    Read-only stock ledger endpoint.

    All records are restricted to the authenticated
    user's active organization.
    """

    serializer_class = StockLedgerMovementSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = InventoryLedgerPagination

    def get_active_organization(self):
        return _get_user_organization(self.request.user)

    def get_queryset(self):
        organization = self.get_active_organization()

        product_id = self.request.query_params.get("product")
        warehouse_id = self.request.query_params.get("warehouse")
        location_id = self.request.query_params.get("location")
        movement_type = self.request.query_params.get("movement_type")
        reference_type = self.request.query_params.get("reference_type")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        product = None
        warehouse = None

        if product_id:
            product = Product.objects.filter(
                id=product_id,
                organization=organization,
            ).first()
            if not product:
                return StockMovement.objects.none()

        if warehouse_id:
            warehouse = Warehouse.objects.filter(
                id=warehouse_id,
                organization=organization,
            ).first()
            if not warehouse:
                return StockMovement.objects.none()

        return StockLedgerSelector.list(
            organization=organization,
            product=product,
            warehouse=warehouse,
            location=location_id if location_id else None,
            movement_type=movement_type,
            reference_type=reference_type,
            start_date=start_date,
            end_date=end_date,
        ).order_by("-created_at", "-id")


class StockLedgerSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_active_organization(self):
        return _get_user_organization(self.request.user)

    def get(self, request):
        organization = self.get_active_organization()

        product_id = request.query_params.get("product")
        warehouse_id = request.query_params.get("warehouse")
        location_id = request.query_params.get("location")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        product = None
        warehouse = None

        if product_id:
            product = Product.objects.filter(
                id=product_id,
                organization=organization,
            ).first()
            if not product:
                return Response({
                    "total_in": 0,
                    "total_out": 0,
                    "net_movement": 0,
                    "movement_count": 0,
                })

        if warehouse_id:
            warehouse = Warehouse.objects.filter(
                id=warehouse_id,
                organization=organization,
            ).first()
            if not warehouse:
                return Response({
                    "total_in": 0,
                    "total_out": 0,
                    "net_movement": 0,
                    "movement_count": 0,
                })

        summary = StockLedgerSelector.summary(
            organization=organization,
            product=product,
            warehouse=warehouse,
            location=location_id if location_id else None,
            start_date=start_date,
            end_date=end_date,
        )

        return Response(summary)
