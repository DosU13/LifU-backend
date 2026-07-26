import hmac

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    ErrorResponseSerializer,
    OkResponseSerializer,
    SessionResponseSerializer,
)
from services.container import SESSION_OWNER_KEY, context_for


class LoginRequestSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)


class LoginView(APIView):
    permission_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: OkResponseSerializer, 401: ErrorResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]

        expected = settings.OWNER_PASSWORD
        # Constant-time compare, and refuse to authenticate at all if no
        # password is configured (otherwise an empty env var would open the game).
        if not expected or not hmac.compare_digest(password, expected):
            return Response(
                {"error": {"code": "INVALID_PASSWORD", "message": "Incorrect password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        request.session[SESSION_OWNER_KEY] = True
        request.session.cycle_key()  # new session id on privilege change
        return Response({"ok": True})


class LogoutView(APIView):
    permission_classes = []

    @extend_schema(request=None, responses={200: OkResponseSerializer})
    def post(self, request: Request) -> Response:
        request.session.flush()
        return Response({"ok": True})


class SessionView(APIView):
    """Lets the SPA discover whether it is already signed in."""

    permission_classes = []

    @extend_schema(responses={200: SessionResponseSerializer})
    def get(self, request: Request) -> Response:
        context = context_for(request)
        return Response(
            {
                "authenticated": context is not None,
                "is_trial": bool(context and context.is_trial),
            }
        )
