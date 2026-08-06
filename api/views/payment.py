from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema

from sales.payments.services import PaymentService
from invoices.views import _get_user_organization
from invoices.models import Invoice
from core.documents.pdf_service import PDFService
from api.serializers.payment import PaymentSerializer
from api.mixins import StandardResponseMixin
from api.pagination import StandardResultsSetPagination


class PaymentViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["receipt_number", "customer__company_name", "reference"]
    ordering_fields = ["payment_date", "created_at", "amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return Payment.objects.filter(organization=org).select_related('customer', 'invoice').prefetch_related('allocations')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            org = _get_user_organization(request.user)
            customer = serializer.validated_data["customer"]
            invoice_id = serializer.validated_data.get("invoice_id")
            invoice = None
            if invoice_id:
                invoice = Invoice.objects.filter(pk=invoice_id, organization=org).first()

            payment = PaymentService.receive_payment(
                organization=org,
                customer=customer,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data.get("payment_method", "BANK"),
                reference=serializer.validated_data.get("reference", ""),
                notes=serializer.validated_data.get("notes", ""),
                invoice=invoice,
                user=request.user
            )
            out_serializer = self.get_serializer(payment)
            return self.success_response(data=out_serializer.data, message="Payment recorded successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{payment.receipt_number}.pdf"'
        PDFService.generate_receipt(payment, response)
        return response
