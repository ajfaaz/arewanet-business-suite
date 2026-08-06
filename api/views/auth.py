from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from api.serializers.auth import UserProfileSerializer
from api.mixins import api_response


class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return api_response(data=serializer.data, message="User profile retrieved successfully.")
