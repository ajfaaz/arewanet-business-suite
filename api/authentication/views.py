from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .serializers import LoginSerializer, PasswordChangeSerializer
from .services import AuthenticationService
from api.utils.responses import success, error


class LoginAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        result = AuthenticationService.login(**serializer.validated_data)
        if not result:
            return error(message="Invalid username or password.", status_code=status.HTTP_401_UNAUTHORIZED)

        user = result.pop("user")
        result["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.get_full_name() or user.username,
        }

        return success(data=result, message="Login successful.")


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org = None
        role = "STAFF"

        if hasattr(user, 'userprofile') and user.userprofile:
            role = user.userprofile.role
            if user.userprofile.organization:
                org = {
                    "id": user.userprofile.organization.id,
                    "name": user.userprofile.organization.name,
                    "slug": user.userprofile.organization.slug
                }

        return success({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.get_full_name() or user.username,
            "role": role,
            "organization": org
        })


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return success(message="Logout successful. Please remove stored authentication tokens.")


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer)
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return error(errors=serializer.errors, message="Validation failed.", status_code=status.HTTP_400_BAD_REQUEST)

        ok, msg = AuthenticationService.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"]
        )

        if not ok:
            return error(message=msg, status_code=status.HTTP_400_BAD_REQUEST)

        return success(message=msg)
