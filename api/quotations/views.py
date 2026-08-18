from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from invoices.models import Quotation
from invoices.views import _get_user_organization
from api.quotations.serializers import (
    QuotationListSerializer,
    QuotationDetailSerializer,
    QuotationCreateSerializer,
)
from api.quotations.services import QuotationAPIService
from api.quotations.selectors import QuotationSelector
from api.invoices.serializers import InvoiceDetailSerializer
from api.utils.responses import success, error
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class QuotationViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    filterset_fields = ["status", "customer"]
    search_fields = ["quotation_no", "customer__company_name"]
    ordering_fields = ["quotation_date", "valid_until", "total"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return QuotationSelector.list(org)

    def get_serializer_class(self):
        if self.action == "list":
            return QuotationListSerializer
        elif self.action == "retrieve":
            return QuotationDetailSerializer
        return QuotationCreateSerializer

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        return QuotationAPIService.create(
            organization=org,
            validated_data=serializer.validated_data,
            user=self.request.user
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success(data=serializer.data, message="Quotations retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                quotation = self.perform_create(serializer)
                out_serializer = QuotationDetailSerializer(quotation)
                return success(data=out_serializer.data, message="Quotation created successfully.", status_code=status.HTTP_201_CREATED)
            except Exception as e:
                return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(data=serializer.data, message="Quotation detail retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        from core.choices import QuotationStatus
        if instance.status != QuotationStatus.DRAFT and instance.status != 'DRAFT':
            return error(message=f"Quotation #{instance.quotation_no} is finalized and cannot be edited.", status_code=status.HTTP_400_BAD_REQUEST)
        
        req_status = request.data.get('status')
        if req_status and req_status.upper() == 'DRAFT' and instance.status != QuotationStatus.DRAFT:
            return error(message="Status downgrade to DRAFT is not permitted.", status_code=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            try:
                serializer.save()
                out_serializer = QuotationDetailSerializer(instance)
                return success(data=out_serializer.data, message="Quotation updated successfully.")
            except Exception as e:
                return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from core.choices import QuotationStatus
        if instance.status != QuotationStatus.DRAFT and instance.status != 'DRAFT':
            return error(message=f"Quotation #{instance.quotation_no} is finalized and cannot be deleted.", status_code=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return success(message="Quotation deleted successfully.")

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        quotation = self.get_object()
        return QuotationAPIService.generate_pdf(quotation, request=request)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        quotation = self.get_object()
        try:
            from invoices.services.quotation_finalization_service import QuotationFinalizationService
            quotation = QuotationFinalizationService.finalize(quotation, user=request.user)
            out_serializer = QuotationDetailSerializer(quotation)
            return success(data=out_serializer.data, message=f"Quotation #{quotation.quotation_no} successfully issued.")
        except Exception as e:
            return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        quotation = self.get_object()
        invoice = QuotationAPIService.convert_to_invoice(quotation=quotation, user=request.user)
        out_serializer = InvoiceDetailSerializer(invoice)
        return success(data=out_serializer.data, message=f"Quotation #{quotation.quotation_no} successfully converted to Invoice #{invoice.invoice_no}.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        quotation = self.get_object()
        QuotationAPIService.approve(quotation=quotation, user=request.user)
        return success(message=f"Quotation #{quotation.quotation_no} approved.")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        quotation = self.get_object()
        QuotationAPIService.reject(quotation=quotation, user=request.user)
        return success(message=f"Quotation #{quotation.quotation_no} rejected.")

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        quotation = self.get_object()
        QuotationAPIService.email_quotation(quotation, request.user)
        return success(message=f"Quotation #{quotation.quotation_no} dispatched via email.")

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        org = _get_user_organization(request.user)
        qs = Quotation.objects.filter(organization=org)
        
        data = {
            "draft": qs.filter(status="DRAFT").count(),
            "sent": qs.filter(status="SENT").count(),
            "approved": qs.filter(status="APPROVED").count(),
            "rejected": qs.filter(status="REJECTED").count(),
            "converted": qs.filter(status="CONVERTED").count(),
            "expired": qs.filter(status="EXPIRED").count(),
            "total_count": qs.count()
        }
        return success(data=data, message="Quotation dashboard metrics retrieved.")
