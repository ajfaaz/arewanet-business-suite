from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.inventory.views import (
    WarehouseViewSet,
    WarehouseLocationViewSet,
    InventoryViewSet,
    StockMovementViewSet,
    GoodsReceivedNoteViewSet,
    GoodsIssueNoteViewSet,
    StockTransferDocumentViewSet,
    StockAdjustmentDocumentViewSet,
)

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='api-warehouse')
router.register(r'locations', WarehouseLocationViewSet, basename='api-warehouse-location')
router.register(r'stock-movements', StockMovementViewSet, basename='api-stock-movement')
router.register(r'movements', StockMovementViewSet, basename='api-stock-movement-alias')
router.register(r'grn', GoodsReceivedNoteViewSet, basename='api-grn')
router.register(r'gin', GoodsIssueNoteViewSet, basename='api-gin')
router.register(r'transfers', StockTransferDocumentViewSet, basename='api-stock-transfer-doc')
router.register(r'adjustments', StockAdjustmentDocumentViewSet, basename='api-stock-adjustment-doc')
router.register(r'', InventoryViewSet, basename='api-inventory')

urlpatterns = [
    path('', include(router.urls)),
]
