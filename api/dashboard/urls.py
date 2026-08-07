from django.urls import path
from .views import (
    DashboardSummaryAPIView,
    RevenueTrendAPIView,
    ReceivablesAPIView,
    TopCustomersAPIView,
    TopProductsAPIView,
    ActivityFeedAPIView,
    NotificationSummaryAPIView,
)

urlpatterns = [
    path("", DashboardSummaryAPIView.as_view(), name="dashboard_summary"),
    path("revenue/", RevenueTrendAPIView.as_view(), name="dashboard_revenue"),
    path("receivables/", ReceivablesAPIView.as_view(), name="dashboard_receivables"),
    path("top-customers/", TopCustomersAPIView.as_view(), name="dashboard_top_customers"),
    path("top-products/", TopProductsAPIView.as_view(), name="dashboard_top_products"),
    path("activity/", ActivityFeedAPIView.as_view(), name="dashboard_activity"),
    path("notifications/", NotificationSummaryAPIView.as_view(), name="dashboard_notifications"),
]
