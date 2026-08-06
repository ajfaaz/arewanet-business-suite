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

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='api-customer')
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'categories', ProductCategoryViewSet, basename='api-category')
router.register(r'quotations', QuotationViewSet, basename='api-quotation')
router.register(r'invoices', InvoiceViewSet, basename='api-invoice')
router.register(r'payments', PaymentViewSet, basename='api-payment')
router.register(r'subscriptions', SubscriptionViewSet, basename='api-subscription')

v1_patterns = [
    # Auth
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserProfileAPIView.as_view(), name='api_user_profile'),

    # Dashboard
    path('dashboard/', DashboardAPIView.as_view(), name='api_dashboard'),

    # Router endpoints
    path('', include(router.urls)),
]

urlpatterns = [
    # API v1 Versioning
    path('v1/', include((v1_patterns, 'v1'))),

    # OpenAPI Schema & Interactive Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
