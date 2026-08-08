from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.inventory.views import (
    WarehouseViewSet,
    WarehouseLocationViewSet,
    InventoryViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='api-warehouse')
router.register(r'locations', WarehouseLocationViewSet, basename='api-warehouse-location')
router.register(r'stock-movements', StockMovementViewSet, basename='api-stock-movement')
router.register(r'movements', StockMovementViewSet, basename='api-stock-movement-alias')
router.register(r'', InventoryViewSet, basename='api-inventory')

urlpatterns = [
    path('', include(router.urls)),
]
