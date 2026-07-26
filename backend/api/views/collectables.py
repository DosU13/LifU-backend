from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    CollectablesStateResponseSerializer,
    CombineRequestSerializer,
    HarmonyRequestSerializer,
    MergeRequestSerializer,
    SellRequestSerializer,
    serialize_stocks,
)
from core.errors import DomainError, InsufficientCollectables, InvalidMerge
from services.container import get_economy_service, get_merger_service, get_repos


def _domain_error_response(exc: DomainError, status_code: int) -> Response:
    return Response({"error": {"code": exc.code, "message": str(exc)}}, status=status_code)


class CollectablesStateView(APIView):
    @extend_schema(responses={200: CollectablesStateResponseSerializer})
    def get(self, request: Request) -> Response:
        repos = get_repos()
        return Response(
            {
                "stocks": serialize_stocks(repos.collectables.get_all()),
                "coins": repos.wallet.get_coins(),
            }
        )


class MergeUpView(APIView):
    @extend_schema(request=MergeRequestSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = MergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        element = serializer.validated_data["element"]
        rarity = serializer.validated_data["rarity"]

        try:
            get_merger_service().merge_up(element, rarity)
        except (InvalidMerge, InsufficientCollectables) as exc:
            return _domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        stocks = serialize_stocks(get_repos().collectables.get_all())
        return Response({"stocks": stocks})


class HarmonyMergeView(APIView):
    @extend_schema(request=HarmonyRequestSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = HarmonyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rarity = serializer.validated_data["rarity"]

        try:
            result = get_merger_service().merge_harmony(rarity)
        except InsufficientCollectables as exc:
            return _domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        stocks = serialize_stocks(get_repos().collectables.get_all())
        return Response({"yield": result.harmony_yield, "extras": result.extras, "stocks": stocks})


class CombineView(APIView):
    @extend_schema(request=CombineRequestSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = CombineRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        element_a = serializer.validated_data["element_a"]
        element_b = serializer.validated_data["element_b"]
        rarity = serializer.validated_data["rarity"]

        try:
            result_element = get_merger_service().combine(element_a, element_b, rarity)
        except (InvalidMerge, InsufficientCollectables) as exc:
            return _domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        stocks = serialize_stocks(get_repos().collectables.get_all())
        return Response({"result_element": result_element.value, "stocks": stocks})


class SellView(APIView):
    @extend_schema(request=SellRequestSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = SellRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        element = serializer.validated_data["element"]
        rarity = serializer.validated_data["rarity"]
        count = serializer.validated_data["count"]

        try:
            coins = get_economy_service().sell(element, rarity, count)
        except InsufficientCollectables as exc:
            return _domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        stocks = serialize_stocks(get_repos().collectables.get_all())
        return Response({"coins": coins, "stocks": stocks})
