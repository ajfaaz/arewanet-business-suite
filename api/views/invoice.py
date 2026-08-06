from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema

from invoices.models import Invoice
from invoices.services.invoice_service import InvoiceService
from invoices.utils.pdf_generator import generate_invoice_pdf
from invoices.views import _get_user_organization
from sales.payments.services import PaymentService
from api.serializers.invoice import InvoiceSerializer, InvoicePaySerializer
from api.serializers.payment import PaymentSerializer
from api.mixins import StandardResponseMixin
from api.pagination import StandardResultsSetPagination


class InvoiceViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_no", "customer__company_name", "project_name"]
    ordering_fields = ["created_at", "invoice_date", "due_date", "total_due"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        qs = Invoice.objects.filter(organization=org).select_related('customer').prefetch_related('items')
        inv_status = self.request.query_params.get("status")
        if inv_status:
            qs = qs.filter(status=inv_status)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            org = _get_user_organization(request.user)
            items_data = serializer.validated_data.pop('items', [])
            customer = serializer.validated_data.pop('customer')

            invoice = InvoiceService.create_invoice(
                organization=org,
                customer=customer,
                invoice_date=serializer.validated_data.get('invoice_date'),
                due_date=serializer.validated_data.get('due_date'),
                items_data=items_data,
                project_name=serializer.validated_data.get('project_name', ''),
                deployment_phase=serializer.validated_data.get('deployment_phase', ''),
                vat=serializer.validated_data.get('vat', 0),
                user=request.user
            )
            out_serializer = self.get_serializer(invoice)
            return self.success_response(data=out_serializer.data, message="Invoice created successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @extend_schema(responses={200: PaymentSerializer}, request=InvoicePaySerializer)
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        invoice = self.get_object()
        serializer = InvoicePaySerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = PaymentService.receive_payment(
                    organization=invoice.organization,
                    customer=invoice.customer,
                    amount=serializer.validated_data["amount"],
                    payment_method=serializer.validated_data["payment_method"],
                    reference=serializer.validated_data.get("reference", ""),
                    notes=serializer.validated_data.get("notes", ""),
                    invoice=invoice,
                    user=request.user
                )
                out_serializer = PaymentSerializer(payment)
                return self.success_response(data=out_serializer.data, message=f"Payment recorded against Invoice #{invoice.invoice_no}.")
            except Exception as e:
                return self.error_response(message=str(e))
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        invoice = self.get_object()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.invoice_no}.pdf"'
        generate_invoice_pdf(response, invoice)
        return response
