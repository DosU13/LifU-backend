import json

from django.urls import reverse

from core.entities import Receptacle
from core.enums import (
    CollectableRarity,
    Element,
    ReceptacleRarity,
    ReceptacleState,
    Virtue,
)
from services import container
from tests.services.test_treasure_service import NOW


def _seed_pool(count: int, rarity=ReceptacleRarity.CHEST, value=20, is_secret=False):
    repo = container.get_repos().receptacles
    created = []
    for i in range(count):
        created.append(
            repo.add(
                Receptacle(
                    id="",
                    state=ReceptacleState.IN_POOL,
                    virtue=Virtue.SERENITY,
                    rarity=rarity,
                    value=value + i,
                    is_generated=False,
                    is_secret=is_secret,
                    friend_name="alex" if is_secret else None,
                    reward_text="secret text" if is_secret else "reward text",
                    content=None,
                    treasure_id=None,
                    created_at=NOW,
                )
            )
        )
    return created


def test_get_treasures_empty_pool_returns_no_treasures(client):
    response = client.get(reverse("treasures"))

    assert response.status_code == 200
    assert response.json()["treasures"] == []


def test_get_treasures_generates_three_slots(client):
    _seed_pool(30)

    response = client.get(reverse("treasures"))

    body = response.json()
    assert len(body["treasures"]) == 3
    assert {t["slot"] for t in body["treasures"]} == {0, 1, 2}
    for treasure in body["treasures"]:
        assert treasure["price"] >= 1
        assert 5 <= len(treasure["contents"]) <= 10


def test_treasure_contents_never_expose_value_or_reward_text(client):
    _seed_pool(10, is_secret=True)

    response = client.get(reverse("treasures"))

    body = response.json()
    payload = json.dumps(body)
    assert "secret text" not in payload
    assert "reward_text" not in payload
    for treasure in body["treasures"]:
        for item in treasure["contents"]:
            assert set(item) == {"virtue", "rarity", "is_secret", "friend_name"}


def test_buy_without_coins_returns_400(client):
    _seed_pool(10)
    treasure_id = client.get(reverse("treasures")).json()["treasures"][0]["id"]

    response = client.post(reverse("treasure-buy", args=[treasure_id]))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_COINS"


def test_buy_happy_path(client, monkeypatch):
    _seed_pool(10)
    container.get_repos().wallet.adjust(1000)
    treasure_id = client.get(reverse("treasures")).json()["treasures"][0]["id"]

    response = client.post(reverse("treasure-buy", args=[treasure_id]))

    assert response.status_code == 200
    body = response.json()
    assert body["drop"]["state"] == "DROPPED"
    assert body["price_paid"] >= 1
    assert body["coins"] == 1000 - body["price_paid"]
    assert "dropped_rarity" in body
    assert set(body["pity"]) == {"VAULT", "SANCTUM"}


def test_buy_unknown_treasure_returns_404(client):
    response = client.post(reverse("treasure-buy", args=["nope"]))
    assert response.status_code == 404


def test_discard_returns_new_treasure_then_blocks_second_attempt(client):
    _seed_pool(30)
    treasures = client.get(reverse("treasures")).json()["treasures"]

    first = client.post(reverse("treasure-discard", args=[treasures[0]["id"]]))
    assert first.status_code == 200
    assert first.json()["new_treasure"] is not None

    second = client.post(reverse("treasure-discard", args=[treasures[1]["id"]]))
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "DISCARD_USED"


# --- opening ---


def _drop_one() -> str:
    """Move a pool receptacle into DROPPED so it can be opened."""
    repo = container.get_repos().receptacles
    receptacle = repo.list_by_state(ReceptacleState.IN_POOL)[0]
    receptacle.state = ReceptacleState.DROPPED
    repo.update(receptacle)
    return receptacle.id


def test_open_without_key_returns_missing_key_with_requirement(client):
    _seed_pool(1)
    receptacle_id = _drop_one()

    response = client.post(reverse("receptacle-open", args=[receptacle_id]))

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "MISSING_KEY"
    # Serenity -> Ocean; a lone receptacle apportions to Chest -> Crystal
    assert error["key_needed"] == {"element": "OCEAN", "rarity": "CRYSTAL"}


def test_open_with_key_consumes_it_and_pays_coins(client):
    _seed_pool(1, value=42)
    container.get_repos().collectables.adjust({(Element.OCEAN, CollectableRarity.CRYSTAL): 1})
    receptacle_id = _drop_one()

    response = client.post(reverse("receptacle-open", args=[receptacle_id]))

    assert response.status_code == 200
    body = response.json()
    assert body["receptacle"]["state"] == "OPENED"
    assert body["coins_gained"] == 42
    assert body["coins"] == 42
    stocks = container.get_repos().collectables.get_all()
    assert stocks[(Element.OCEAN, CollectableRarity.CRYSTAL)] == 0


def test_open_reveals_secret_reward_text(client):
    _seed_pool(1, is_secret=True)
    container.get_repos().collectables.adjust({(Element.OCEAN, CollectableRarity.CRYSTAL): 1})
    receptacle_id = _drop_one()

    response = client.post(reverse("receptacle-open", args=[receptacle_id]))

    assert response.json()["receptacle"]["reward_text"] == "secret text"


def test_open_receptacle_not_dropped_returns_400(client):
    created = _seed_pool(1)[0]
    container.get_repos().collectables.adjust({(Element.OCEAN, CollectableRarity.CRYSTAL): 1})

    response = client.post(reverse("receptacle-open", args=[created.id]))

    assert response.status_code == 400


def test_open_unknown_receptacle_returns_404(client):
    response = client.post(reverse("receptacle-open", args=["nope"]))
    assert response.status_code == 404


# --- state snapshot ---


def test_state_returns_full_snapshot(client):
    _seed_pool(10)
    container.get_repos().wallet.adjust(250)

    response = client.get(reverse("state"))

    assert response.status_code == 200
    body = response.json()
    assert body["coins"] == 250
    assert len(body["stocks"]) == 96
    assert len(body["treasures"]) >= 1
    assert body["dropped_receptacles"] == []
    assert set(body["stats"]) == {"per_day", "virtue_means", "streak"}


def test_state_never_leaks_secret_text(client):
    _seed_pool(10, is_secret=True)

    response = client.get(reverse("state"))

    assert "secret text" not in json.dumps(response.json())
