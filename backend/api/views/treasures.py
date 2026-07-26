from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import serialize_receptacle, serialize_stocks
from core.enums import ReceptacleState
from core.errors import DiscardAlreadyUsed, DomainError, InsufficientCoins, MissingKey, NotFound
from services.container import (
    get_repos,
    get_reward_service,
    get_stats_service,
    get_treasure_service,
)


def _error(exc: DomainError, status_code: int) -> Response:
    return Response({"error": {"code": exc.code, "message": str(exc)}}, status=status_code)


def _serialize_treasure(service, treasure) -> dict:
    """Treasure summary. Contents deliberately omit value and reward text —

    what is inside stays a surprise until it drops.
    """
    return {
        "id": treasure.id,
        "slot": treasure.slot,
        "price": service.price(treasure),
        "pity": {rarity.name: count for rarity, count in treasure.pity.items()},
        "contents": [
            {
                "virtue": r.virtue.value,
                "rarity": r.rarity.name,
                "is_secret": r.is_secret,
                "friend_name": r.friend_name,
            }
            for r in service.contents(treasure)
        ],
    }


class TreasureListView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        service = get_treasure_service()
        treasures = service.get_all()
        return Response({"treasures": [_serialize_treasure(service, t) for t in treasures]})


class TreasureBuyView(APIView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request: Request, treasure_id: str) -> Response:
        service = get_treasure_service()
        try:
            result = service.buy(treasure_id)
        except NotFound as exc:
            return _error(exc, status.HTTP_404_NOT_FOUND)
        except InsufficientCoins as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "drop": serialize_receptacle(result.receptacle),
                "dropped_rarity": result.dropped_rarity.name,
                "was_pity": result.was_pity,
                "price_paid": result.price_paid,
                "coins": result.coins,
                "pity": {rarity.name: count for rarity, count in result.pity.items()},
                "treasure_gone": result.treasure_gone,
            }
        )


class TreasureDiscardView(APIView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request: Request, treasure_id: str) -> Response:
        service = get_treasure_service()
        try:
            new_treasure = service.discard(treasure_id)
        except NotFound as exc:
            return _error(exc, status.HTTP_404_NOT_FOUND)
        except DiscardAlreadyUsed as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)

        payload = _serialize_treasure(service, new_treasure) if new_treasure else None
        return Response({"new_treasure": payload})


class ReceptacleOpenView(APIView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request: Request, receptacle_id: str) -> Response:
        try:
            receptacle, coins_gained, coins = get_reward_service().open_receptacle(receptacle_id)
        except NotFound as exc:
            return _error(exc, status.HTTP_404_NOT_FOUND)
        except MissingKey as exc:
            return Response(
                {
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                        "key_needed": {
                            "element": exc.element.value,
                            "rarity": exc.rarity.name,
                        },
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DomainError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "receptacle": serialize_receptacle(receptacle),
                "coins_gained": coins_gained,
                "coins": coins,
            }
        )


class StateView(APIView):
    """One call that boots the whole SPA (ARCHITECTURE §9)."""

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        repos = get_repos()
        treasure_service = get_treasure_service()
        treasures = treasure_service.get_all()
        stats = get_stats_service().get_stats()

        return Response(
            {
                "coins": repos.wallet.get_coins(),
                "stocks": serialize_stocks(repos.collectables.get_all()),
                "treasures": [_serialize_treasure(treasure_service, t) for t in treasures],
                "dropped_receptacles": [
                    serialize_receptacle(r)
                    for r in get_reward_service().list_by_state(ReceptacleState.DROPPED)
                ],
                "stats": {
                    "per_day": stats.per_day,
                    "virtue_means": {v.value: m for v, m in stats.virtue_means.items()},
                    "streak": stats.streak,
                },
            }
        )
