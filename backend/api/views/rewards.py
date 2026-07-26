from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import RewardCreateRequestSerializer, serialize_receptacle
from core.enums import ReceptacleState
from core.errors import AIResponseInvalid


class RewardCreateView(APIView):
    @extend_schema(request=RewardCreateRequestSerializer, responses={200: dict})
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

        return Response(serialize_receptacle(receptacle))


class ReceptacleListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "state",
                str,
                description="Filter by state: IN_POOL, IN_TREASURE, DROPPED, OPENED",
            )
        ],
        responses={200: dict},
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
