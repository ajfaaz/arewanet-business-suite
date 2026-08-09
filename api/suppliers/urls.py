from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.suppliers.views import SupplierViewSet

router = DefaultRouter()
router.register(r"", SupplierViewSet, basename="supplier")

urlpatterns = [
    path("", include(router.urls)),
]
