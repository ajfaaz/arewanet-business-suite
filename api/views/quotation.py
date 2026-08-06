from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from invoices.models import Quotation
from sales.services.quotation_service import QuotationService
from invoices.views import _get_user_organization
from api.serializers.quotation import QuotationSerializer
from api.serializers.invoice import InvoiceSerializer
from api.mixins import StandardResponseMixin
from api.pagination import StandardResultsSetPagination


class QuotationViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuotationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["quotation_no", "customer__company_name", "notes"]
    ordering_fields = ["created_at", "quotation_no"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return Quotation.objects.filter(organization=org).select_related('customer').prefetch_related('items')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            org = _get_user_organization(request.user)
            items_data = serializer.validated_data.pop('items', [])
            quotation = Quotation(
                organization=org,
                **serializer.validated_data
            )
            qtn = QuotationService.create(quotation, items_data, user=request.user)
            out_serializer = self.get_serializer(qtn)
            return self.success_response(data=out_serializer.data, message="Quotation created successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @extend_schema(responses={200: InvoiceSerializer})
    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        quotation = self.get_object()
        try:
            invoice = QuotationService.convert_to_invoice(quotation, user=request.user)
            out_serializer = InvoiceSerializer(invoice)
            return self.success_response(data=out_serializer.data, message=f"Quotation converted to Invoice #{invoice.invoice_no}.")
        except Exception as e:
            return self.error_response(message=str(e))
