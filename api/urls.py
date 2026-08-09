from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from api.views import (
    UserProfileAPIView,
    CustomerViewSet,
    ProductViewSet,
    ProductCategoryViewSet,
    QuotationViewSet,
    InvoiceViewSet,
    PaymentViewSet,
    SubscriptionViewSet,
    DashboardAPIView,
)

from api.views.health import HealthCheckAPIView

router = DefaultRouter()
router.register(r'categories', ProductCategoryViewSet, basename='api-category')
router.register(r'subscriptions', SubscriptionViewSet, basename='api-subscription')

urlpatterns = [
    # Health Check Endpoint
    path('health/', HealthCheckAPIView.as_view(), name='health'),

    # Auth Module
    path('auth/', include('api.authentication.urls')),

    # Customers Module
    path('customers/', include('api.customers.urls')),

    # Products Module
    path('products/', include('api.products.urls')),

    # Invoices Module
    path('invoices/', include('api.invoices.urls')),

    # Payments Module
    path('payments/', include('api.payments.urls')),

    # Quotations Module
    path('quotations/', include('api.quotations.urls')),

    # Dashboard Module
    path('dashboard/', include('api.dashboard.urls')),

    # Inventory Module
    path('inventory/', include('api.inventory.urls')),
    path('warehouses/', include('api.inventory.urls')),

    # Suppliers & Purchase Orders Module
    path('suppliers/', include('api.suppliers.urls')),
    path('purchase-orders/', include('api.purchases.urls')),

    # OpenAPI Schema & Interactive Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Router endpoints
    path('', include(router.urls)),
]
