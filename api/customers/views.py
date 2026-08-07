from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.http import HttpResponse

from invoices.models import Customer, ActivityLog
from invoices.views import _get_user_organization
from sales.services.statement_service import StatementService
from core.documents.pdf_service import PDFService
from api.customers.serializers import (
    CustomerSerializer,
    CustomerListSerializer,
    CustomerDetailSerializer,
)
from api.utils.responses import success, error
from api.pagination import StandardResultsSetPagination


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["company_name", "contact_person", "email", "phone"]
    ordering_fields = ["company_name", "created_at"]
    ordering = ["company_name"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return Customer.objects.filter(organization=org)

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer
        elif self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerSerializer

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
        return success(data=serializer.data, message="Customers retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return success(data=serializer.data, message="Customer created successfully.", status_code=status.HTTP_201_CREATED)
        return error(errors=serializer.errors, message="Validation failed.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(data=serializer.data, message="Customer detail retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return success(data=serializer.data, message="Customer updated successfully.")
        return error(errors=serializer.errors, message="Validation failed.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success(message="Customer deleted successfully.")

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        customer = self.get_object()
        invoices = customer.invoice_set.all()

        total_revenue = sum((inv.total_paid for inv in invoices), 0)
        outstanding = sum((inv.balance_due for inv in invoices if inv.status != 'CANCELLED'), 0)
        quotations_count = customer.quotation_set.count() if hasattr(customer, 'quotation_set') else 0
        payments_count = customer.sales_payments.count() if hasattr(customer, 'sales_payments') else customer.payments.count()

        data = {
            "customer": customer.company_name,
            "revenue": float(total_revenue),
            "outstanding": float(outstanding),
            "invoices": invoices.count(),
            "payments": payments_count,
            "quotations": quotations_count,
        }
        return success(data=data, message="Customer summary retrieved.")

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        customer = self.get_object()
        timeline_events = []

        for inv in customer.invoice_set.all().order_by('-created_at')[:10]:
            timeline_events.append({
                "type": "Invoice",
                "title": f"Invoice #{inv.invoice_no} ({inv.get_status_display()})",
                "date": str(inv.invoice_date or inv.created_at.date())
            })

        for qtn in customer.quotation_set.all().order_by('-created_at')[:10]:
            timeline_events.append({
                "type": "Quotation",
                "title": f"Quotation #{qtn.quotation_no} ({qtn.get_status_display()})",
                "date": str(qtn.quotation_date or qtn.created_at.date())
            })

        payments_qs = customer.sales_payments.all() if hasattr(customer, 'sales_payments') else customer.payments.all()
        for pmt in payments_qs.order_by('-created_at')[:10]:
            timeline_events.append({
                "type": "Payment",
                "title": f"Payment Received ({pmt.receipt_number})",
                "date": str(pmt.payment_date)
            })

        timeline_events.sort(key=lambda x: x["date"], reverse=True)
        return success(data=timeline_events, message="Customer timeline retrieved.")

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        customer = self.get_object()
        stmt = StatementService.generate_statement(customer)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Statement_{customer.company_name.replace(" ", "_")}.pdf"'
        PDFService.generate_statement(stmt, response)
        return response

    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        customer = self.get_object()
        invoices = customer.invoice_set.all()

        paid = sum((inv.total_paid for inv in invoices), 0)
        outstanding = sum((inv.balance_due for inv in invoices if inv.status != 'CANCELLED'), 0)
        subscriptions_count = customer.subscriptions.count() if hasattr(customer, 'subscriptions') else 0
        payments_count = customer.sales_payments.count() if hasattr(customer, 'sales_payments') else customer.payments.count()

        # Score calculation: ratio of paid vs total billing
        total_billed = paid + outstanding
        score = 100 if total_billed == 0 else int((paid / total_billed) * 100)

        data = {
            "outstanding": float(outstanding),
            "paid": float(paid),
            "invoices": invoices.count(),
            "payments": payments_count,
            "subscriptions": subscriptions_count,
            "score": score
        }
        return success(data=data, message="Customer 360° dashboard metrics retrieved.")
