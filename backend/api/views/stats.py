from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import StatsResponseSerializer


class StatsView(APIView):
    @extend_schema(responses={200: StatsResponseSerializer})
    def get(self, request: Request) -> Response:
        stats = request.game_context.stats_service().get_stats()
        return Response(StatsResponseSerializer(stats).data)
