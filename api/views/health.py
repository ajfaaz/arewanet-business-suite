from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from api.utils.responses import success


class HealthCheckAPIView(APIView):
    """
    Lightweight health check endpoint for uptime monitoring, Docker, and load balancers.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return success(data={"status": "ok"}, message="API is healthy.")
