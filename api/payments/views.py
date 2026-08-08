from decimal import Decimal
from datetime import date, timedelta
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone

from sales.payments.models import Payment
from invoices.views import _get_user_organization
from api.payments.serializers import (
    PaymentListSerializer,
    PaymentDetailSerializer,
    PaymentCreateSerializer,
)
from api.payments.services import PaymentAPIService
from api.payments.selectors import PaymentSelector
from api.utils.responses import success, error
from api.pagination import StandardResultsSetPagination


from core.api import OrganizationModelViewSet
from core.permissions import IsOrganizationMember


class PaymentViewSet(OrganizationModelViewSet):
    permission_classes = [IsOrganizationMember]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["receipt_number", "reference", "invoice__invoice_no", "customer__company_name"]
    ordering_fields = ["payment_date", "amount", "created_at"]
    ordering = ["-payment_date", "-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return PaymentSelector.list(org)

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        elif self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentCreateSerializer

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        return PaymentAPIService.receive(
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
        return success(data=serializer.data, message="Payments retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = self.perform_create(serializer)
                out_serializer = PaymentDetailSerializer(payment)
                return success(data=out_serializer.data, message="Payment received successfully.", status_code=status.HTTP_201_CREATED)
            except Exception as e:
                return error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(data=serializer.data, message="Payment detail retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            out_serializer = PaymentDetailSerializer(instance)
            return success(data=out_serializer.data, message="Payment updated successfully.")
        return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success(message="Payment record deleted successfully.")

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        response = PaymentAPIService.generate_receipt_pdf(payment, None)
        return response

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        payment = self.get_object()
        ok, msg = PaymentAPIService.reverse(payment=payment, user=request.user)
        if not ok:
            return error(message=msg, status_code=status.HTTP_400_BAD_REQUEST)
        return success(message=msg)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        payment = self.get_object()
        events = [
            {
                "event": f"Payment Received ({payment.receipt_number})",
                "date": str(payment.payment_date)
            },
            {
                "event": f"Receipt #{payment.receipt_number} Generated",
                "date": str(payment.payment_date)
            }
        ]
        if payment.status == "REVERSED":
            events.append({
                "event": "Payment Reversed",
                "date": str(payment.updated_at.date() if hasattr(payment, 'updated_at') else date.today())
            })
        return success(data=events, message="Payment timeline retrieved.")

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        org = _get_user_organization(request.user)
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        completed_payments = Payment.objects.filter(organization=org, status="COMPLETED")

        today_val = completed_payments.filter(payment_date=today).aggregate(tot=Sum('amount'))['tot'] or Decimal("0.00")
        week_val = completed_payments.filter(payment_date__gte=week_ago).aggregate(tot=Sum('amount'))['tot'] or Decimal("0.00")
        month_val = completed_payments.filter(payment_date__gte=month_start).aggregate(tot=Sum('amount'))['tot'] or Decimal("0.00")
        year_val = completed_payments.filter(payment_date__gte=year_start).aggregate(tot=Sum('amount'))['tot'] or Decimal("0.00")

        pending_count = Payment.objects.filter(organization=org, status="PENDING").count()
        reversed_count = Payment.objects.filter(organization=org, status="REVERSED").count()

        data = {
            "today": float(today_val),
            "week": float(week_val),
            "month": float(month_val),
            "year": float(year_val),
            "pending": pending_count,
            "reversed": reversed_count
        }
        return success(data=data, message="Payment dashboard metrics retrieved.")

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        payment = self.get_object()
        PaymentAPIService.email_receipt(payment, request.user)
        return success(message=f"Receipt #{payment.receipt_number} dispatched via email.")

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        org = _get_user_organization(request.user)
        qs = Payment.objects.filter(organization=org, status="COMPLETED")
        
        breakdown = {}
        for row in qs.values('payment_method').annotate(count=Count('id'), total=Sum('amount')):
            method_key = (row['payment_method'] or 'OTHER').lower()
            breakdown[method_key] = {
                "count": row['count'],
                "total": float(row['total'] or 0)
            }

        return success(data=breakdown, message="Payment method analytics retrieved.")
