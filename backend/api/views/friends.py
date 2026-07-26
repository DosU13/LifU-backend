import re

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import AlreadyExists
from services.container import owner_context
from services.trial import get_trial_store

FRIEND_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")


def friend_url(name: str) -> str:
    return f"{settings.FRIEND_LINK_BASE_URL}/{name}"


class FriendCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=31, trim_whitespace=True)

    def validate_name(self, value: str) -> str:
        slug = value.strip().lower()
        if not FRIEND_NAME_PATTERN.match(slug):
            raise serializers.ValidationError(
                "Use 1-31 characters: lowercase letters, digits, hyphen or underscore."
            )
        return slug


class FriendLinkListCreateView(APIView):
    """Owner-only: friend links are how the owner hands out trial URLs."""

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        if request.game_context.is_trial:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Owner only."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        links = request.game_context.repos.friend_links.list_all()
        return Response(
            {"friends": [{"name": link.name, "url": friend_url(link.name)} for link in links]}
        )

    @extend_schema(request=FriendCreateRequestSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        if request.game_context.is_trial:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Owner only."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = FriendCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]

        try:
            link = request.game_context.repos.friend_links.add(name)
        except AlreadyExists as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"name": link.name, "url": friend_url(link.name)})


class PublicFriendCheckView(APIView):
    """Unauthenticated: lets a friend page confirm its link before offering a trial."""

    permission_classes = []

    @extend_schema(responses={200: dict})
    def get(self, request: Request, name: str) -> Response:
        link = owner_context().repos.friend_links.get(name.strip().lower())
        return Response({"valid": link is not None, "name": name})


class TrialSessionSerializer(serializers.Serializer):
    friend_name = serializers.CharField(max_length=31, trim_whitespace=True)


class TrialSessionView(APIView):
    """Unauthenticated: issues a sandbox token for a valid friend link.

    The sandbox is entirely in memory — nothing a friend does here can reach
    the owner's real game.
    """

    permission_classes = []

    @extend_schema(request=TrialSessionSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = TrialSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        friend_name = serializer.validated_data["friend_name"].strip().lower()

        if owner_context().repos.friend_links.get(friend_name) is None:
            return Response(
                {
                    "error": {
                        "code": "UNKNOWN_FRIEND",
                        "message": "That link is not recognised. Ask Doslan for one.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        session = get_trial_store().create(friend_name)
        return Response(
            {
                "token": session.token,
                "friend_name": session.friend_name,
                "expires_at": session.expires_at,
            }
        )


