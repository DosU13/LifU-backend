from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission

from services.container import context_for


class GamePermission(BasePermission):
    """Allow only the logged-in owner or a valid trial token.

    Resolves the caller's GameContext once and stashes it on the request, so
    views never re-derive who they are serving.

    Lives apart from api/auth.py on purpose: DRF resolves
    DEFAULT_PERMISSION_CLASSES while importing rest_framework.views, so this
    module must not pull that in.
    """

    def has_permission(self, request, view) -> bool:
        context = context_for(request)
        request.game_context = context
        if context is None:
            # Raised rather than returning False: with no authentication
            # classes configured, DRF would otherwise answer 403, and "you are
            # not signed in" is a 401.
            raise NotAuthenticated("Sign in, or use a valid trial link.")
        return True
