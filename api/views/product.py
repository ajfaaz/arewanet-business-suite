from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from invoices.models import Product, ProductCategory
from invoices.views import _get_user_organization
from api.serializers.product import ProductSerializer, ProductCategorySerializer
from api.mixins import StandardResponseMixin
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class ProductViewSet(StandardResponseMixin, OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "selling_price", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        qs = Product.objects.filter(organization=org)
        cat_id = self.request.query_params.get("category")
        if cat_id:
            qs = qs.filter(category_id=cat_id)
        return qs

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        serializer.save(organization=org)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return self.success_response(data=serializer.data, message="Product created successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")


class ProductCategoryViewSet(StandardResponseMixin, OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return ProductCategory.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        serializer.save(organization=org)
