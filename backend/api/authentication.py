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
