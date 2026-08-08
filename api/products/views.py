from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Sum, Count

from invoices.models import Product, InvoiceItem
from sales.models import QuotationItem
from invoices.views import _get_user_organization
from api.products.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
)
from api.products.services import ProductService
from api.products.selectors import ProductSelector
from api.utils.responses import success, error
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class ProductViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    filterset_fields = ["category"]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "selling_price", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        qs = ProductSelector.list(org)

        # Filters
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        is_active_param = self.request.query_params.get("is_active")
        if is_active_param is not None:
            active_bool = is_active_param.lower() in ["true", "1"]
            qs = qs.filter(active=active_bool)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        elif self.action == "retrieve":
            return ProductDetailSerializer
        return ProductCreateSerializer

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        return ProductService.create(
            organization=org,
            validated_data=serializer.validated_data
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success(data=serializer.data, message="Products retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product = self.perform_create(serializer)
            out_serializer = ProductDetailSerializer(product)
            return success(data=out_serializer.data, message="Product created successfully.", status_code=status.HTTP_201_CREATED)
        return error(errors=serializer.errors, message="Validation failed.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(data=serializer.data, message="Product detail retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            out_serializer = ProductDetailSerializer(instance)
            return success(data=out_serializer.data, message="Product updated successfully.")
        return error(errors=serializer.errors, message="Validation failed.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success(message="Product deleted successfully.")

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        product = self.get_object()

        invoice_items = InvoiceItem.objects.filter(product=product)
        sold_qty = invoice_items.aggregate(total_qty=Sum('qty'))['total_qty'] or 0
        revenue = invoice_items.aggregate(total_rev=Sum('total'))['total_rev'] or 0

        quotation_count = QuotationItem.objects.filter(product=product).count()
        invoice_count = invoice_items.values('invoice').distinct().count()

        data = {
            "product": product.name,
            "sold_quantity": float(sold_qty),
            "revenue": float(revenue),
            "stock": 18,  # Inventory module placeholder
            "quotation_count": quotation_count,
            "invoice_count": invoice_count,
        }
        return success(data=data, message="Product summary retrieved.")

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        product = self.get_object()
        data = {
            "available": 25,
            "reserved": 8,
            "damaged": 1,
            "reorder_level": 10,
        }
        return success(data=data, message="Product stock levels retrieved.")

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def image(self, request, pk=None):
        product = self.get_object()
        if 'image' not in request.FILES:
            return error(message="No image file provided.", status_code=status.HTTP_400_BAD_REQUEST)

        product.image = request.FILES['image']
        product.save()
        out_serializer = ProductDetailSerializer(product)
        return success(data=out_serializer.data, message="Product image uploaded successfully.")
