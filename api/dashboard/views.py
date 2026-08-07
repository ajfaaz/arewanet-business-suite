from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from invoices.views import _get_user_organization
from api.dashboard.services import DashboardAPIService
from api.dashboard.serializers import (
    DashboardSummarySerializer,
    RevenueTrendSerializer,
    ReceivablesSerializer,
    TopCustomerSerializer,
    TopProductSerializer,
    ActivityFeedSerializer,
    NotificationSummarySerializer,
)
from api.utils.responses import success, error


class DashboardSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSummarySerializer

    @extend_schema(
        summary="Retrieve main ERP dashboard summary metrics",
        description="Returns core KPIs including daily sales, monthly sales, revenue, MRR, outstanding receivables, customer count, product count, and active subscriptions.",
        responses={200: DashboardSummarySerializer}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_summary(org)
        return success(data=data, message="Dashboard summary metrics retrieved successfully.")


class RevenueTrendAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueTrendSerializer

    @extend_schema(
        summary="Retrieve monthly revenue trend analysis",
        description="Returns monthly historical revenue collections for line and bar chart visualizations.",
        responses={200: RevenueTrendSerializer(many=True)}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_revenue_trend(org)
        return success(data=data, message="Revenue trend analytics retrieved successfully.")


class ReceivablesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReceivablesSerializer

    @extend_schema(
        summary="Retrieve accounts receivable aging breakdown",
        description="Returns outstanding receivables grouped into aging buckets: current, 30 days, 60 days, and 90+ days overdue.",
        responses={200: ReceivablesSerializer}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_receivables(org)
        return success(data=data, message="Receivables aging breakdown retrieved successfully.")


class TopCustomersAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopCustomerSerializer

    @extend_schema(
        summary="Retrieve top customers by total revenue",
        description="Returns top customers sorted by total paid invoice revenue.",
        responses={200: TopCustomerSerializer(many=True)}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_top_customers(org)
        return success(data=data, message="Top customers retrieved successfully.")


class TopProductsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopProductSerializer

    @extend_schema(
        summary="Retrieve top selling products by quantity",
        description="Returns top products sorted by total invoiced sales quantity.",
        responses={200: TopProductSerializer(many=True)}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_top_products(org)
        return success(data=data, message="Top selling products retrieved successfully.")


class ActivityFeedAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityFeedSerializer

    @extend_schema(
        summary="Retrieve recent audit activity logs",
        description="Returns the latest audit feed events for invoices, payments, quotations, and system operations.",
        responses={200: ActivityFeedSerializer(many=True)}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_recent_activity(org)
        return success(data=data, message="Recent activity feed retrieved successfully.")


class NotificationSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSummarySerializer

    @extend_schema(
        summary="Retrieve action-required notifications summary",
        description="Returns counts for overdue invoices, expiring quotations, and subscriptions due for billing.",
        responses={200: NotificationSummarySerializer}
    )
    def get(self, request):
        org = _get_user_organization(request.user)
        data = DashboardAPIService.get_notifications(org)
        return success(data=data, message="Notification summary retrieved successfully.")
