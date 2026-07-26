from django.urls import reverse
from rest_framework.test import APIClient

from core.enums import BASE_ELEMENTS, CollectableRarity, Element
from services import container


class _ScriptedRng:
    def __init__(self, values):
        self._values = list(values)

    def random(self) -> float:
        return self._values.pop(0)


def _seed_stock(stock: dict) -> None:
    container.get_repos().collectables.adjust(stock)


def test_get_collectables_empty_initially():
    client = APIClient()
    response = client.get(reverse("collectables"))

    assert response.status_code == 200
    body = response.json()
    assert body["coins"] == 0
    assert len(body["stocks"]) == 96
    assert body["stocks"]["FIRE_FRAGMENT"] == 0


def test_merge_up_happy_path():
    _seed_stock({(Element.FIRE, CollectableRarity.FRAGMENT): 3})
    client = APIClient()

    response = client.post(
        reverse("collectables-merge"),
        {"element": "FIRE", "rarity": "FRAGMENT"},
        format="json",
    )

    assert response.status_code == 200
    stocks = response.json()["stocks"]
    assert stocks["FIRE_FRAGMENT"] == 0
    assert stocks["FIRE_SHARD"] == 1


def test_merge_up_rejects_core():
    _seed_stock({(Element.FIRE, CollectableRarity.CORE): 3})
    client = APIClient()

    response = client.post(
        reverse("collectables-merge"),
        {"element": "FIRE", "rarity": "CORE"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERGE"


def test_merge_up_insufficient_stock():
    client = APIClient()
    response = client.post(
        reverse("collectables-merge"),
        {"element": "FIRE", "rarity": "FRAGMENT"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_COLLECTABLES"


def test_merge_up_rejects_unknown_element():
    client = APIClient()
    response = client.post(
        reverse("collectables-merge"),
        {"element": "NOT_AN_ELEMENT", "rarity": "FRAGMENT"},
        format="json",
    )
    assert response.status_code == 400


def test_harmony_merge_happy_path(monkeypatch):
    _seed_stock({(e, CollectableRarity.FRAGMENT): 1 for e in BASE_ELEMENTS})
    monkeypatch.setattr(container, "get_rng", lambda: _ScriptedRng([0.9]))  # fails immediately
    client = APIClient()

    response = client.post(
        reverse("collectables-harmony"), {"rarity": "FRAGMENT"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["yield"] == 5
    assert body["extras"] == 0
    assert body["stocks"]["HARMONY_FRAGMENT"] == 5
    for element in BASE_ELEMENTS:
        assert body["stocks"][f"{element.value}_FRAGMENT"] == 0


def test_harmony_merge_insufficient_stock(monkeypatch):
    monkeypatch.setattr(container, "get_rng", lambda: _ScriptedRng([0.9]))
    client = APIClient()

    response = client.post(
        reverse("collectables-harmony"), {"rarity": "FRAGMENT"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_COLLECTABLES"


def test_combine_happy_path():
    _seed_stock(
        {
            (Element.FIRE, CollectableRarity.SHARD): 1,
            (Element.AIR, CollectableRarity.SHARD): 1,
            (Element.HARMONY, CollectableRarity.SHARD): 1,
        }
    )
    client = APIClient()

    response = client.post(
        reverse("collectables-combine"),
        {"element_a": "FIRE", "element_b": "AIR", "rarity": "SHARD"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_element"] == "LIGHTNING"
    assert body["stocks"]["LIGHTNING_SHARD"] == 1
    assert body["stocks"]["FIRE_SHARD"] == 0
    assert body["stocks"]["AIR_SHARD"] == 0
    assert body["stocks"]["HARMONY_SHARD"] == 0


def test_combine_rejects_invalid_pair():
    _seed_stock(
        {
            (Element.FIRE, CollectableRarity.SHARD): 5,
            (Element.HARMONY, CollectableRarity.SHARD): 5,
        }
    )
    client = APIClient()

    response = client.post(
        reverse("collectables-combine"),
        {"element_a": "FIRE", "element_b": "FIRE", "rarity": "SHARD"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERGE"


def test_sell_happy_path():
    _seed_stock({(Element.EARTH, CollectableRarity.CRYSTAL): 5})
    client = APIClient()

    response = client.post(
        reverse("collectables-sell"),
        {"element": "EARTH", "rarity": "CRYSTAL", "count": 3},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["coins"] == 9 * 3
    assert body["stocks"]["EARTH_CRYSTAL"] == 2


def test_sell_insufficient_stock():
    client = APIClient()
    response = client.post(
        reverse("collectables-sell"),
        {"element": "EARTH", "rarity": "CRYSTAL", "count": 1},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_COLLECTABLES"


def test_sell_rejects_non_positive_count():
    _seed_stock({(Element.EARTH, CollectableRarity.CRYSTAL): 5})
    client = APIClient()

    response = client.post(
        reverse("collectables-sell"),
        {"element": "EARTH", "rarity": "CRYSTAL", "count": 0},
        format="json",
    )

    assert response.status_code == 400
