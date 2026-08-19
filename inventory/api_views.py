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


from decimal import Decimal
from rest_framework import status
from invoices.models import Invoice
from inventory.models import GoodsIssueNote
from inventory.document_services import GoodsIssueService
from core.exceptions import BusinessRuleError, InsufficientStockError, WarehouseOrganizationMismatch


class InvoiceCreateGoodsIssueAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_active_organization(self):
        return _get_user_organization(self.request.user)

    def post(self, request, invoice_id):
        organization = self.get_active_organization()
        invoice = generics.get_object_or_404(
            Invoice,
            id=invoice_id,
            organization=organization,
        )

        warehouse_id = request.data.get("warehouse_id")
        items_data = request.data.get("items", [])
        document_number = request.data.get("document_number")

        if not warehouse_id:
            return Response(
                {"error": "warehouse_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        warehouse = generics.get_object_or_404(
            Warehouse,
            id=warehouse_id,
            organization=organization,
        )

        if not document_number:
            import uuid
            document_number = f"GIN-{invoice.invoice_no}-{uuid.uuid4().hex[:6].upper()}"

        items = []
        for item in items_data:
            product = generics.get_object_or_404(
                Product,
                id=item.get("product_id"),
                organization=organization,
            )
            items.append({
                "product": product,
                "quantity": Decimal(str(item.get("quantity", "0"))),
            })

        try:
            gin = GoodsIssueService.create_from_invoice(
                invoice=invoice,
                warehouse=warehouse,
                created_by=request.user,
                items=items,
                document_number=document_number,
            )
            return Response({
                "success": True,
                "id": gin.id,
                "document_number": gin.document_number,
                "status": gin.status,
                "invoice_id": gin.invoice_id,
            }, status=status.HTTP_201_CREATED)
        except (BusinessRuleError, WarehouseOrganizationMismatch, InsufficientStockError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GoodsIssueSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        organization = _get_user_organization(request.user)
        gin = generics.get_object_or_404(GoodsIssueNote, id=pk, organization=organization)
        try:
            submitted_gin = GoodsIssueService.submit(gin)
            return Response({
                "success": True,
                "id": submitted_gin.id,
                "document_number": submitted_gin.document_number,
                "status": submitted_gin.status,
            })
        except BusinessRuleError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GoodsIssueApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        organization = _get_user_organization(request.user)
        gin = generics.get_object_or_404(GoodsIssueNote, id=pk, organization=organization)
        try:
            approved_gin = GoodsIssueService.approve(gin, approved_by=request.user)
            return Response({
                "success": True,
                "id": approved_gin.id,
                "document_number": approved_gin.document_number,
                "status": approved_gin.status,
            })
        except (BusinessRuleError, InsufficientStockError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GoodsIssueCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        organization = _get_user_organization(request.user)
        gin = generics.get_object_or_404(GoodsIssueNote, id=pk, organization=organization)
        try:
            completed_gin, movements = GoodsIssueService.complete(gin, completed_by=request.user)
            return Response({
                "success": True,
                "id": completed_gin.id,
                "document_number": completed_gin.document_number,
                "status": completed_gin.status,
                "movement_count": len(movements),
            })
        except (BusinessRuleError, InsufficientStockError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

