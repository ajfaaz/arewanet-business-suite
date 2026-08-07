from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginAPIView, MeAPIView, LogoutAPIView, ChangePasswordAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api-login"),
    path("refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("me/", MeAPIView.as_view(), name="api-me"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="api-change-password"),
]
