from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from invoices.views import _get_user_organization
from invoices.models import Product
from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember
from api.utils.responses import success, error
from inventory.models import (
    Warehouse, WarehouseLocation, InventoryItem, StockMovement,
    GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
)
from inventory.selectors import (
    WarehouseSelector, WarehouseLocationSelector, InventorySelector, StockMovementSelector,
    GoodsReceivedNoteSelector, GoodsIssueNoteSelector, StockTransferDocumentSelector, StockAdjustmentDocumentSelector
)
from inventory.services import StockService
from inventory.document_services import InventoryDocumentService
from api.inventory.serializers import (
    WarehouseSerializer,
    WarehouseLocationSerializer,
    InventoryItemSerializer,
    StockMovementSerializer,
    StockOperationSerializer,
    StockAdjustmentSerializer,
    StockTransferSerializer,
    GoodsReceivedNoteSerializer,
    GoodsIssueNoteSerializer,
    StockTransferDocumentSerializer,
    StockAdjustmentDocumentSerializer,
)


class WarehouseViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = WarehouseSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "code", "address"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return WarehouseSelector.list(org)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)
        org = _get_user_organization(request.user)
        serializer.save(organization=org)
        return success(data=serializer.data, message="Warehouse created successfully.", status_code=status.HTTP_201_CREATED)


class WarehouseLocationViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = WarehouseLocationSerializer
    filterset_fields = ["warehouse", "is_active"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return WarehouseLocation.objects.filter(warehouse__organization=org).select_related("warehouse")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return success(data=serializer.data, message="Location created successfully.", status_code=status.HTTP_201_CREATED)


class InventoryViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = InventoryItemSerializer
    filterset_fields = ["product", "warehouse", "location"]
    search_fields = ["product__name", "product__sku", "warehouse__name", "warehouse__code"]
    ordering_fields = ["quantity", "updated_at"]
    ordering = ["product__name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return InventorySelector.list(org)

    @action(detail=False, methods=["post"])
    def receive(self, request):
        serializer = StockOperationSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        org = _get_user_organization(request.user)
        data = serializer.validated_data

        product = Product.objects.filter(organization=org, id=data["product"]).first()
        if not product:
            return error(message="Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        warehouse = Warehouse.objects.filter(organization=org, id=data["warehouse"]).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        location = None
        if data.get("location"):
            location = WarehouseLocation.objects.filter(warehouse=warehouse, id=data["location"]).first()
            if not location:
                return error(message="Warehouse location not found.", status_code=status.HTTP_404_NOT_FOUND)

        movement = StockService.receive(
            product=product,
            warehouse=warehouse,
            quantity=data["quantity"],
            location=location,
            reference_type=data.get("reference_type") or "",
            reference_id=data.get("reference_id"),
            notes=data.get("notes") or "",
        )

        balance = StockService.get_balance(product, warehouse=warehouse, location=location)

        return success(
            data={
                "product": product.id,
                "product_name": product.name,
                "warehouse": warehouse.id,
                "warehouse_name": warehouse.name,
                "quantity": data["quantity"],
                "balance": balance,
                "movement_id": movement.id,
            },
            message="Stock received successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def issue(self, request):
        serializer = StockOperationSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        org = _get_user_organization(request.user)
        data = serializer.validated_data

        product = Product.objects.filter(organization=org, id=data["product"]).first()
        if not product:
            return error(message="Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        warehouse = Warehouse.objects.filter(organization=org, id=data["warehouse"]).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        location = None
        if data.get("location"):
            location = WarehouseLocation.objects.filter(warehouse=warehouse, id=data["location"]).first()
            if not location:
                return error(message="Warehouse location not found.", status_code=status.HTTP_404_NOT_FOUND)

        movement = StockService.issue(
            product=product,
            warehouse=warehouse,
            quantity=data["quantity"],
            location=location,
            reference_type=data.get("reference_type") or "",
            reference_id=data.get("reference_id"),
            notes=data.get("notes") or "",
        )

        balance = StockService.get_balance(product, warehouse=warehouse, location=location)

        return success(
            data={
                "product": product.id,
                "product_name": product.name,
                "warehouse": warehouse.id,
                "warehouse_name": warehouse.name,
                "quantity": data["quantity"],
                "balance": balance,
                "movement_id": movement.id,
            },
            message="Stock issued successfully.",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        org = _get_user_organization(request.user)
        data = serializer.validated_data

        product = Product.objects.filter(organization=org, id=data["product"]).first()
        if not product:
            return error(message="Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        warehouse = Warehouse.objects.filter(organization=org, id=data["warehouse"]).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        location = None
        if data.get("location"):
            location = WarehouseLocation.objects.filter(warehouse=warehouse, id=data["location"]).first()
            if not location:
                return error(message="Warehouse location not found.", status_code=status.HTTP_404_NOT_FOUND)

        movement = StockService.adjust(
            product=product,
            warehouse=warehouse,
            new_quantity=data["quantity"],
            location=location,
            reference_type=data.get("reference_type") or "",
            reference_id=data.get("reference_id"),
            notes=data.get("notes") or "",
        )

        balance = StockService.get_balance(product, warehouse=warehouse, location=location)

        return success(
            data={
                "product": product.id,
                "product_name": product.name,
                "warehouse": warehouse.id,
                "warehouse_name": warehouse.name,
                "new_balance": balance,
                "movement_id": movement.id if movement else None,
            },
            message="Stock balance adjusted successfully.",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        serializer = StockTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        org = _get_user_organization(request.user)
        data = serializer.validated_data

        product = Product.objects.filter(organization=org, id=data["product"]).first()
        if not product:
            return error(message="Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        from_wh = Warehouse.objects.filter(organization=org, id=data["from_warehouse"]).first()
        if not from_wh:
            return error(message="Source warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        to_wh = Warehouse.objects.filter(organization=org, id=data["to_warehouse"]).first()
        if not to_wh:
            return error(message="Destination warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        from_loc = None
        if data.get("from_location"):
            from_loc = WarehouseLocation.objects.filter(warehouse=from_wh, id=data["from_location"]).first()
            if not from_loc:
                return error(message="Source location not found.", status_code=status.HTTP_404_NOT_FOUND)

        to_loc = None
        if data.get("to_location"):
            to_loc = WarehouseLocation.objects.filter(warehouse=to_wh, id=data["to_location"]).first()
            if not to_loc:
                return error(message="Destination location not found.", status_code=status.HTTP_404_NOT_FOUND)

        out_mv, in_mv = StockService.transfer(
            product=product,
            from_warehouse=from_wh,
            to_warehouse=to_wh,
            quantity=data["quantity"],
            from_location=from_loc,
            to_location=to_loc,
            reference_type=data.get("reference_type") or "",
            reference_id=data.get("reference_id"),
            notes=data.get("notes") or "",
        )

        from_bal = StockService.get_balance(product, warehouse=from_wh, location=from_loc)
        to_bal = StockService.get_balance(product, warehouse=to_wh, location=to_loc)

        return success(
            data={
                "product": product.id,
                "quantity": data["quantity"],
                "source_warehouse": from_wh.name,
                "source_balance": from_bal,
                "destination_warehouse": to_wh.name,
                "destination_balance": to_bal,
            },
            message=f"Transferred {data['quantity']} units from {from_wh.name} to {to_wh.name}.",
            status_code=status.HTTP_200_OK,
        )


class StockMovementViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = StockMovementSerializer
    filterset_fields = ["product", "warehouse", "location", "movement_type"]
    search_fields = ["product__name", "product__sku", "warehouse__name", "reference_type", "notes"]
    ordering_fields = ["created_at", "quantity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return StockMovementSelector.list(org)


# -------------------------------------------------------------------------
# Inventory Document ViewSets
# -------------------------------------------------------------------------

class GoodsReceivedNoteViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = GoodsReceivedNoteSerializer
    filterset_fields = ["status", "warehouse"]
    search_fields = ["document_number", "supplier_name", "warehouse__name"]
    ordering_fields = ["created_at", "received_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return GoodsReceivedNoteSelector.list(org)

    def create(self, request, *args, **kwargs):
        org = _get_user_organization(request.user)
        wh_id = request.data.get("warehouse")
        warehouse = Warehouse.objects.filter(organization=org, id=wh_id).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        received_date = request.data.get("received_date")
        items_data = request.data.get("items", [])
        if not received_date or not items_data:
            return error(message="received_date and items list are required.", status_code=status.HTTP_400_BAD_REQUEST)

        formatted_items = []
        for item in items_data:
            product = Product.objects.filter(organization=org, id=item.get("product")).first()
            if not product:
                return error(message=f"Product {item.get('product')} not found.", status_code=status.HTTP_404_NOT_FOUND)
            formatted_items.append({
                "product": product,
                "quantity": item.get("quantity"),
                "unit_cost": item.get("unit_cost")
            })

        grn = InventoryDocumentService.create_grn(
            organization=org,
            warehouse=warehouse,
            received_date=received_date,
            items_data=formatted_items,
            supplier_name=request.data.get("supplier_name", ""),
            notes=request.data.get("notes", ""),
            user=request.user
        )

        serializer = self.get_serializer(grn)
        return success(data=serializer.data, message="Goods Received Note created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        grn = self.get_object()
        grn = InventoryDocumentService.submit_grn(grn)
        return success(data=self.get_serializer(grn).data, message="GRN submitted for review.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        grn = self.get_object()
        grn = InventoryDocumentService.approve_grn(grn, user=request.user)
        return success(data=self.get_serializer(grn).data, message="GRN approved.")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        grn = self.get_object()
        grn = InventoryDocumentService.complete_grn(grn, user=request.user)
        return success(data=self.get_serializer(grn).data, message="GRN completed and stock updated.")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        grn = self.get_object()
        grn = InventoryDocumentService.cancel_grn(grn)
        return success(data=self.get_serializer(grn).data, message="GRN cancelled.")


class GoodsIssueNoteViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = GoodsIssueNoteSerializer
    filterset_fields = ["status", "warehouse"]
    search_fields = ["document_number", "warehouse__name"]
    ordering_fields = ["created_at", "issue_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return GoodsIssueNoteSelector.list(org)

    def create(self, request, *args, **kwargs):
        org = _get_user_organization(request.user)
        wh_id = request.data.get("warehouse")
        warehouse = Warehouse.objects.filter(organization=org, id=wh_id).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        issue_date = request.data.get("issue_date")
        items_data = request.data.get("items", [])
        if not issue_date or not items_data:
            return error(message="issue_date and items list are required.", status_code=status.HTTP_400_BAD_REQUEST)

        formatted_items = []
        for item in items_data:
            product = Product.objects.filter(organization=org, id=item.get("product")).first()
            if not product:
                return error(message=f"Product {item.get('product')} not found.", status_code=status.HTTP_404_NOT_FOUND)
            formatted_items.append({
                "product": product,
                "quantity": item.get("quantity")
            })

        gin = InventoryDocumentService.create_gin(
            organization=org,
            warehouse=warehouse,
            issue_date=issue_date,
            items_data=formatted_items,
            notes=request.data.get("notes", ""),
            user=request.user
        )

        serializer = self.get_serializer(gin)
        return success(data=serializer.data, message="Goods Issue Note created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        gin = self.get_object()
        gin = InventoryDocumentService.submit_gin(gin)
        return success(data=self.get_serializer(gin).data, message="GIN submitted for review.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        gin = self.get_object()
        gin = InventoryDocumentService.approve_gin(gin, user=request.user)
        return success(data=self.get_serializer(gin).data, message="GIN approved.")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        gin = self.get_object()
        gin = InventoryDocumentService.complete_gin(gin, user=request.user)
        return success(data=self.get_serializer(gin).data, message="GIN completed and stock issued.")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        gin = self.get_object()
        gin = InventoryDocumentService.cancel_gin(gin)
        return success(data=self.get_serializer(gin).data, message="GIN cancelled.")


class StockTransferDocumentViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = StockTransferDocumentSerializer
    filterset_fields = ["status", "source_warehouse", "destination_warehouse"]
    search_fields = ["document_number", "source_warehouse__name", "destination_warehouse__name"]
    ordering_fields = ["created_at", "transfer_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return StockTransferDocumentSelector.list(org)

    def create(self, request, *args, **kwargs):
        org = _get_user_organization(request.user)
        src_wh_id = request.data.get("source_warehouse")
        dest_wh_id = request.data.get("destination_warehouse")

        src_wh = Warehouse.objects.filter(organization=org, id=src_wh_id).first()
        dest_wh = Warehouse.objects.filter(organization=org, id=dest_wh_id).first()
        if not src_wh or not dest_wh:
            return error(message="Source or Destination warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        transfer_date = request.data.get("transfer_date")
        items_data = request.data.get("items", [])
        if not transfer_date or not items_data:
            return error(message="transfer_date and items list are required.", status_code=status.HTTP_400_BAD_REQUEST)

        formatted_items = []
        for item in items_data:
            product = Product.objects.filter(organization=org, id=item.get("product")).first()
            if not product:
                return error(message=f"Product {item.get('product')} not found.", status_code=status.HTTP_404_NOT_FOUND)
            formatted_items.append({
                "product": product,
                "quantity": item.get("quantity")
            })

        transfer_doc = InventoryDocumentService.create_transfer(
            organization=org,
            source_warehouse=src_wh,
            destination_warehouse=dest_wh,
            transfer_date=transfer_date,
            items_data=formatted_items,
            notes=request.data.get("notes", ""),
            user=request.user
        )

        serializer = self.get_serializer(transfer_doc)
        return success(data=serializer.data, message="Stock Transfer Document created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        transfer_doc = self.get_object()
        transfer_doc = InventoryDocumentService.submit_transfer(transfer_doc)
        return success(data=self.get_serializer(transfer_doc).data, message="Transfer submitted for review.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        transfer_doc = self.get_object()
        transfer_doc = InventoryDocumentService.approve_transfer(transfer_doc, user=request.user)
        return success(data=self.get_serializer(transfer_doc).data, message="Transfer approved.")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        transfer_doc = self.get_object()
        transfer_doc = InventoryDocumentService.complete_transfer(transfer_doc, user=request.user)
        return success(data=self.get_serializer(transfer_doc).data, message="Stock transfer completed.")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        transfer_doc = self.get_object()
        transfer_doc = InventoryDocumentService.cancel_transfer(transfer_doc)
        return success(data=self.get_serializer(transfer_doc).data, message="Transfer cancelled.")


class StockAdjustmentDocumentViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = StockAdjustmentDocumentSerializer
    filterset_fields = ["status", "warehouse"]
    search_fields = ["document_number", "warehouse__name"]
    ordering_fields = ["created_at", "adjustment_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return StockAdjustmentDocumentSelector.list(org)

    def create(self, request, *args, **kwargs):
        org = _get_user_organization(request.user)
        wh_id = request.data.get("warehouse")
        warehouse = Warehouse.objects.filter(organization=org, id=wh_id).first()
        if not warehouse:
            return error(message="Warehouse not found.", status_code=status.HTTP_404_NOT_FOUND)

        adjustment_date = request.data.get("adjustment_date")
        items_data = request.data.get("items", [])
        if not adjustment_date or not items_data:
            return error(message="adjustment_date and items list are required.", status_code=status.HTTP_400_BAD_REQUEST)

        formatted_items = []
        for item in items_data:
            product = Product.objects.filter(organization=org, id=item.get("product")).first()
            if not product:
                return error(message=f"Product {item.get('product')} not found.", status_code=status.HTTP_404_NOT_FOUND)
            formatted_items.append({
                "product": product,
                "counted_quantity": item.get("counted_quantity"),
                "reason": item.get("reason", "")
            })

        adj = InventoryDocumentService.create_adjustment(
            organization=org,
            warehouse=warehouse,
            adjustment_date=adjustment_date,
            items_data=formatted_items,
            notes=request.data.get("notes", ""),
            user=request.user
        )

        serializer = self.get_serializer(adj)
        return success(data=serializer.data, message="Stock Adjustment Document created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        adj = self.get_object()
        adj = InventoryDocumentService.submit_adjustment(adj)
        return success(data=self.get_serializer(adj).data, message="Adjustment submitted for review.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        adj = self.get_object()
        adj = InventoryDocumentService.approve_adjustment(adj, user=request.user)
        return success(data=self.get_serializer(adj).data, message="Adjustment approved.")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        adj = self.get_object()
        adj = InventoryDocumentService.complete_adjustment(adj, user=request.user)
        return success(data=self.get_serializer(adj).data, message="Stock adjustment completed.")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        adj = self.get_object()
        adj = InventoryDocumentService.cancel_adjustment(adj)
        return success(data=self.get_serializer(adj).data, message="Adjustment cancelled.")
