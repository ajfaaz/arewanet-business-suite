from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from drf_spectacular.utils import extend_schema

from invoices.models import Customer, Product, Invoice
from sales.payments.models import Payment
from sales.subscriptions.services import SubscriptionService
from invoices.views import _get_user_organization
from api.mixins import api_response


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        org = _get_user_organization(request.user)

        invoices = Invoice.objects.filter(organization=org)
        customers_count = Customer.objects.filter(organization=org).count()
        products_count = Product.objects.filter(organization=org).count()
        invoices_count = invoices.count()

        total_revenue = Payment.objects.filter(
            organization=org,
            status="COMPLETED"
        ).aggregate(total=Sum('amount'))['total'] or 0

        outstanding = sum((inv.balance_due for inv in invoices.exclude(status='CANCELLED')), 0)

        sub_metrics = SubscriptionService.calculate_mrr_arr(org)

        data = {
            "revenue": float(total_revenue),
            "outstanding": float(outstanding),
            "customers": customers_count,
            "products": products_count,
            "invoices": invoices_count,
            "mrr": float(sub_metrics["mrr"]),
            "arr": float(sub_metrics["arr"]),
        }

        return api_response(data=data, message="Dashboard metrics retrieved successfully.")
