from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from drf_spectacular.utils import extend_schema, OpenApiParameter

from invoices.models import Customer, Invoice
from invoices.views import _get_user_organization
from api.serializers.customer import CustomerSerializer, CustomerSummarySerializer
from api.mixins import api_response, StandardResponseMixin
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class CustomerViewSet(StandardResponseMixin, OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = CustomerSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["company_name", "contact_person", "email", "phone"]
    ordering_fields = ["company_name", "created_at"]
    ordering = ["company_name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return Customer.objects.filter(organization=org)

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
            return self.success_response(data=serializer.data, message="Customer created successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return self.success_response(data=serializer.data, message="Customer updated successfully.")
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @extend_schema(responses={200: CustomerSummarySerializer})
    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        customer = self.get_object()

        invoices = customer.invoice_set.all()
        total_due = invoices.aggregate(total=Sum('total_due'))['total'] or 0
        total_paid = sum((inv.total_paid for inv in invoices), 0)
        outstanding = sum((inv.balance_due for inv in invoices), 0)

        data = {
            "customer": customer.company_name,
            "outstanding": outstanding,
            "paid": total_paid,
            "quotations": customer.quotations.count() if hasattr(customer, 'quotations') else 0,
            "invoices": invoices.count(),
            "payments": customer.payments.count() if hasattr(customer, 'payments') else 0,
        }

        return self.success_response(data=data, message="Customer summary retrieved.")
