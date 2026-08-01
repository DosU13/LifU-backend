from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    ErrorResponseSerializer,
    ReceptacleListResponseSerializer,
    RewardCreateRequestSerializer,
    RewardListResponseSerializer,
    RewardResponseSerializer,
    serialize_receptacle,
    serialize_reward,
)
from core.enums import ReceptacleState
from core.errors import AIResponseInvalid


class RewardView(APIView):
    """Rewards as their author sees them.

    Both directions deliberately say nothing about receptacles: which one a
    reward was sealed into is the surprise. `GET /api/receptacles` is the
    mirror image — receptacles without their contents.
    """

    @extend_schema(responses={200: RewardListResponseSerializer})
    def get(self, request: Request) -> Response:
        receptacles = request.game_context.repos.receptacles.list_non_generated()
        receptacles.sort(key=lambda r: r.created_at, reverse=True)
        return Response({"rewards": [serialize_reward(r) for r in receptacles]})

    @extend_schema(
        request=RewardCreateRequestSerializer,
        responses={200: RewardResponseSerializer, 502: ErrorResponseSerializer},
        description=(
            "Seal a reward into a receptacle. The response deliberately does not say "
            "which receptacle it became — that is the surprise."
        ),
    )
    def post(self, request: Request) -> Response:
        serializer = RewardCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            receptacle = request.game_context.reward_service().submit_reward(
                text=data["text"],
                is_secret=data["is_secret"],
                friend_name=data.get("friend_name"),
            )
        except AIResponseInvalid:
            return Response(
                {"error": {"code": "AI_INVALID", "message": "The AI response was invalid."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(serialize_reward(receptacle))


class ReceptacleListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "state",
                str,
                description="Filter by state: IN_POOL, IN_TREASURE, DROPPED, OPENED",
            )
        ],
        responses={200: ReceptacleListResponseSerializer, 400: ErrorResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        state_param = request.query_params.get("state")
        if state_param is None:
            state = ReceptacleState.DROPPED
        else:
            try:
                state = ReceptacleState(state_param.upper())
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "INVALID_STATE",
                            "message": f"Unknown receptacle state: {state_param!r}",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        receptacles = request.game_context.reward_service().list_by_state(state)
        return Response({"receptacles": [serialize_receptacle(r) for r in receptacles]})
