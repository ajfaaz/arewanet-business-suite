from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet
from inventory.api_views import InvoiceCreateGoodsIssueAPIView

router = DefaultRouter()
router.register(r"", InvoiceViewSet, basename="invoices")

urlpatterns = [
    path("<int:invoice_id>/goods-issues/", InvoiceCreateGoodsIssueAPIView.as_view(), name="invoice-create-gin-api"),
] + router.urls
