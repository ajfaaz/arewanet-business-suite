from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from invoices.views import _get_user_organization
from invoices.models import Product
from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember
from api.utils.responses import success, error
from inventory.models import Warehouse, WarehouseLocation, InventoryItem, StockMovement
from inventory.selectors import WarehouseSelector, WarehouseLocationSelector, InventorySelector, StockMovementSelector
from inventory.services import StockService
from api.inventory.serializers import (
    WarehouseSerializer,
    WarehouseLocationSerializer,
    InventoryItemSerializer,
    StockMovementSerializer,
    StockOperationSerializer,
    StockAdjustmentSerializer,
    StockTransferSerializer,
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
