import json

from django.urls import reverse

from aiclients.fake import FakeAIClient
from core.enums import ReceptacleState
from services import container


def _use_fake_ai(monkeypatch, responses):
    fake = FakeAIClient(responses)
    monkeypatch.setattr(container, "get_ai_client", lambda: fake)
    return fake


def test_post_reward_happy_path(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 42, "Class": ["Serenity"]}])

    response = client.post(reverse("rewards"), {"text": "a quiet evening"}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "a quiet evening"
    assert body["is_secret"] is False
    assert body["is_opened"] is False


def test_post_reward_does_not_say_which_receptacle_it_became(client, monkeypatch):
    """Sealing is supposed to be a surprise, so the response stays quiet.

    Fully covered in tests/api/test_privacy.py; kept here because this
    endpoint used to answer with the receptacle and must never go back to it.
    """
    _use_fake_ai(monkeypatch, [{"Value": 42, "Class": ["Serenity"]}])

    body = client.post(reverse("rewards"), {"text": "reward"}, format="json").json()

    for leaked in ("virtue", "rarity", "value", "key_needed", "id", "state"):
        assert leaked not in body


def test_post_reward_missing_text_rejected(client, monkeypatch):
    _use_fake_ai(monkeypatch, [])

    response = client.post(reverse("rewards"), {}, format="json")

    assert response.status_code == 400


def test_post_reward_ai_failure_returns_502(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"bad": 1}, {"bad": 1}, {"bad": 1}])

    response = client.post(reverse("rewards"), {"text": "text"}, format="json")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID"


# --- the secret privacy rule ---

SECRET_TEXT = "I promise you a lunch if you open this chest"


def test_secret_reward_text_is_never_returned_on_create(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 85, "Class": ["Nurturing"]}])

    response = client.post(
        reverse("rewards"),
        {"text": SECRET_TEXT, "is_secret": True, "friend_name": "alex"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_secret"] is True
    assert body["friend_name"] == "alex"
    assert body["text"] is None
    # belt and braces: the text must not appear anywhere in the payload
    assert SECRET_TEXT not in json.dumps(body)


def test_secret_reward_text_is_never_returned_when_listing(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 85, "Class": ["Nurturing"]}])
    client.post(
        reverse("rewards"),
        {"text": SECRET_TEXT, "is_secret": True, "friend_name": "alex"},
        format="json",
    )

    response = client.get(reverse("receptacles"), {"state": "IN_POOL"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["receptacles"]) == 1
    assert body["receptacles"][0]["reward_text"] is None
    assert SECRET_TEXT not in json.dumps(body)


def test_secret_reward_text_is_revealed_once_opened(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 85, "Class": ["Nurturing"]}])
    client.post(
        reverse("rewards"),
        {"text": SECRET_TEXT, "is_secret": True},
        format="json",
    )

    repo = container.get_repos().receptacles
    receptacle = repo.list_non_generated()[0]
    receptacle.state = ReceptacleState.OPENED
    repo.update(receptacle)

    response = client.get(reverse("receptacles"), {"state": "OPENED"})

    body = response.json()
    assert body["receptacles"][0]["reward_text"] == SECRET_TEXT


def test_own_reward_text_is_hidden_until_opened(client, monkeypatch):
    """Not only secret gifts: a reward the owner wrote is withheld too.

    Rarity is apportioned by value, so showing the text alongside the rarity
    would rank the owner's whole wishlist and leave nothing to discover.
    """
    _use_fake_ai(monkeypatch, [{"Value": 20, "Class": ["Freedom"]}])
    client.post(reverse("rewards"), {"text": "movie night"}, format="json")

    sealed = client.get(reverse("receptacles"), {"state": "IN_POOL"}).json()
    assert sealed["receptacles"][0]["reward_text"] is None

    repo = container.get_repos().receptacles
    receptacle = repo.list_non_generated()[0]
    receptacle.state = ReceptacleState.OPENED
    repo.update(receptacle)

    opened = client.get(reverse("receptacles"), {"state": "OPENED"}).json()
    assert opened["receptacles"][0]["reward_text"] == "movie night"


# --- listing ---


def test_get_receptacles_defaults_to_dropped_state(client):
    response = client.get(reverse("receptacles"))

    assert response.status_code == 200
    assert response.json()["receptacles"] == []


def test_get_receptacles_rejects_unknown_state(client):
    response = client.get(reverse("receptacles"), {"state": "NONSENSE"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATE"
