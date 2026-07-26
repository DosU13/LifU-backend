from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness check — no auth, no dependencies."""

    @extend_schema(responses={200: {"type": "object", "properties": {"ok": {"type": "boolean"}}}})
    def get(self, request: Request) -> Response:
        return Response({"ok": True})
