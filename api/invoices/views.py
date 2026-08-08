from decimal import Decimal
from datetime import date
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q

from invoices.models import Invoice, ActivityLog
from invoices.views import _get_user_organization
from sales.payments.services import PaymentService
from api.invoices.serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
)
from api.invoices.services import InvoiceService
from api.invoices.selectors import InvoiceSelector
from api.utils.responses import success, error
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class InvoiceViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_no", "customer__company_name"]
    ordering_fields = ["invoice_date", "due_date", "total_due"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return InvoiceSelector.list(org)

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        elif self.action == "retrieve":
            return InvoiceDetailSerializer
        return InvoiceCreateSerializer

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        return InvoiceService.create(
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
        return success(data=serializer.data, message="Invoices retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            invoice = self.perform_create(serializer)
            out_serializer = InvoiceDetailSerializer(invoice)
            return success(data=out_serializer.data, message="Invoice created successfully.", status_code=status.HTTP_201_CREATED)
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(data=serializer.data, message="Invoice detail retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            out_serializer = InvoiceDetailSerializer(instance)
            return success(data=out_serializer.data, message="Invoice updated successfully.")
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success(message="Invoice deleted successfully.")

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        invoice = self.get_object()
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{invoice.invoice_no}.pdf"'
        return InvoiceService.generate_pdf(invoice, response)

    @action(detail=False, methods=["get"], url_path="public/(?P<token>[^/.]+)", permission_classes=[AllowAny])
    def public(self, request, token=None):
        invoice = Invoice.objects.filter(public_token=token).first()
        if not invoice:
            return error(message="Public invoice not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = InvoiceDetailSerializer(invoice)
        return success(data=serializer.data, message="Public invoice retrieved successfully.")

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        invoice = self.get_object()
        amount = request.data.get("amount")
        payment_method = request.data.get("method", "BANK_TRANSFER")
        reference = request.data.get("reference", "")

        if not amount:
            return error(message="Payment amount is required.", status_code=status.HTTP_400_BAD_REQUEST)

        org = _get_user_organization(request.user)
        pmt = PaymentService.receive_payment(
            organization=org,
            customer=invoice.customer,
            amount=amount,
            payment_method=payment_method,
            reference=reference,
            invoice=invoice,
            user=request.user
        )

        invoice.refresh_from_db()
        return success(
            data={
                "receipt_number": pmt.receipt_number,
                "amount": float(pmt.amount),
                "invoice_status": invoice.status,
                "balance_due": float(invoice.balance_due)
            },
            message="Payment recorded successfully."
        )

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        invoice = self.get_object()
        payment_list = []
        payments_qs = invoice.sales_payments.all() if hasattr(invoice, 'sales_payments') else invoice.payments.all()
        for pmt in payments_qs.order_by("-payment_date"):
            payment_list.append({
                "id": pmt.id,
                "receipt_number": pmt.receipt_number,
                "amount": float(pmt.amount),
                "payment_method": getattr(pmt, 'payment_method', 'CASH'),
                "payment_date": str(pmt.payment_date)
            })
        return success(data=payment_list, message="Payment history retrieved.")

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        invoice = self.get_object()
        events = [
            {
                "type": "Invoice",
                "title": f"Invoice #{invoice.invoice_no} Created",
                "date": str(invoice.invoice_date or invoice.created_at.date())
            }
        ]

        payments_qs = invoice.sales_payments.all() if hasattr(invoice, 'sales_payments') else invoice.payments.all()
        for pmt in payments_qs.order_by("payment_date"):
            events.append({
                "type": "Payment",
                "title": f"Payment Received ({pmt.receipt_number})",
                "date": str(pmt.payment_date)
            })

        return success(data=events, message="Invoice timeline retrieved.")

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        invoice = self.get_object()
        data = {
            "invoice": float(invoice.total_due),
            "paid": float(invoice.total_paid),
            "balance": float(invoice.balance_due)
        }
        return success(data=data, message="Outstanding balance retrieved.")

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        invoice = self.get_object()
        InvoiceService.email_invoice(invoice, request.user)
        return success(message=f"Invoice #{invoice.invoice_no} sent via email.")

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        invoice = self.get_object()
        new_inv = InvoiceService.duplicate(invoice)
        serializer = InvoiceDetailSerializer(new_inv)
        return success(data=serializer.data, message=f"Invoice duplicated into #{new_inv.invoice_no}.")

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        org = _get_user_organization(request.user)
        invoices = Invoice.objects.filter(organization=org)

        draft = invoices.filter(status="DRAFT").count()
        unpaid = invoices.filter(status="UNPAID").count()
        paid = invoices.filter(status="PAID").count()
        overdue = invoices.filter(status="OVERDUE").count()

        outstanding = sum((inv.balance_due for inv in invoices if inv.status != 'CANCELLED'), 0)
        collected = sum((inv.total_paid for inv in invoices), 0)

        data = {
            "draft": draft,
            "unpaid": unpaid,
            "paid": paid,
            "overdue": overdue,
            "outstanding": float(outstanding),
            "collected": float(collected)
        }
        return success(data=data, message="Invoice dashboard metrics retrieved.")
