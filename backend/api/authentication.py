from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication


class GameAuthentication(BaseAuthentication):
    """Carries no credentials of its own.

    Who the caller is gets decided in `GamePermission` (owner session cookie
    or X-Trial-Token). This class exists purely so DRF has an
    `authenticate_header` to offer: without one it rewrites NotAuthenticated
    into 403, and "you are not signed in" should be a 401.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request) -> str:
        return "Session"


class GameAuthenticationScheme(OpenApiAuthenticationExtension):
    """Describes the two ways in for /api/docs.

    Registered by import (drf-spectacular discovers subclasses), so swagger
    shows the trial header alongside the owner's session cookie.
    """

    target_class = "api.authentication.GameAuthentication"
    name = "trialToken"

    def get_security_definition(self, auto_schema) -> dict:
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-Trial-Token",
            "description": (
                "A friend's sandbox token from POST /api/trial/session. "
                "The owner instead authenticates with the session cookie set "
                "by POST /api/auth/login."
            ),
        }
