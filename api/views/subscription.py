from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from sales.subscriptions.models import Subscription, SubscriptionTemplate
from sales.subscriptions.services import SubscriptionService
from invoices.views import _get_user_organization
from api.serializers.subscription import SubscriptionSerializer, SubscriptionTemplateSerializer
from api.serializers.invoice import InvoiceSerializer
from api.mixins import StandardResponseMixin
from api.pagination import StandardResultsSetPagination


from core.permissions import IsOrganizationMember


class SubscriptionViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsOrganizationMember]
    serializer_class = SubscriptionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "customer__company_name", "notes"]
    ordering_fields = ["created_at", "next_invoice_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = _get_user_organization(self.request.user)
        return Subscription.objects.filter(organization=org).select_related('customer', 'template').prefetch_related('items')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            org = _get_user_organization(request.user)
            items_data = serializer.validated_data.pop('items', [])
            customer = serializer.validated_data.pop('customer')

            sub = SubscriptionService.create_subscription(
                organization=org,
                customer=customer,
                title=serializer.validated_data['title'],
                start_date=serializer.validated_data['start_date'],
                billing_cycle=serializer.validated_data.get('billing_cycle', 'MONTHLY'),
                auto_generate=serializer.validated_data.get('auto_generate', True),
                items_data=items_data,
                template=serializer.validated_data.get('template'),
                notes=serializer.validated_data.get('notes', ''),
                user=request.user
            )
            out_serializer = self.get_serializer(sub)
            return self.success_response(data=out_serializer.data, message="Subscription created successfully.", status_code=status.HTTP_201_CREATED)
        return self.error_response(errors=serializer.errors, message="Validation failed.")

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        sub = self.get_object()
        sub = SubscriptionService.pause(sub, user=request.user)
        out_serializer = self.get_serializer(sub)
        return self.success_response(data=out_serializer.data, message=f"Subscription '{sub.title}' paused.")

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        sub = self.get_object()
        sub = SubscriptionService.resume(sub, user=request.user)
        out_serializer = self.get_serializer(sub)
        return self.success_response(data=out_serializer.data, message=f"Subscription '{sub.title}' resumed.")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sub = self.get_object()
        sub = SubscriptionService.cancel(sub, user=request.user)
        out_serializer = self.get_serializer(sub)
        return self.success_response(data=out_serializer.data, message=f"Subscription '{sub.title}' cancelled.")

    @extend_schema(responses={200: InvoiceSerializer})
    @action(detail=True, methods=["post"])
    def generate_invoice(self, request, pk=None):
        sub = self.get_object()
        try:
            invoice = SubscriptionService.generate_invoice(sub, user=request.user)
            out_serializer = InvoiceSerializer(invoice)
            return self.success_response(data=out_serializer.data, message=f"Invoice #{invoice.invoice_no} generated.")
        except Exception as e:
            return self.error_response(message=str(e))
