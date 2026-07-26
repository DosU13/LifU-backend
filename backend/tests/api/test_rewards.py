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
    assert body["value"] == 42
    assert body["virtue"] == "SERENITY"
    assert body["state"] == "IN_POOL"
    assert body["is_secret"] is False
    assert body["reward_text"] == "a quiet evening"


def test_post_reward_includes_key_needed(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 42, "Class": ["Serenity"]}])

    response = client.post(reverse("rewards"), {"text": "reward"}, format="json")

    body = response.json()
    # Serenity maps to Ocean; a lone receptacle apportions to Chest -> Crystal key
    assert body["rarity"] == "CHEST"
    assert body["key_needed"] == {"element": "OCEAN", "rarity": "CRYSTAL"}


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
    assert body["reward_text"] is None
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
    created = client.post(
        reverse("rewards"),
        {"text": SECRET_TEXT, "is_secret": True},
        format="json",
    ).json()

    # simulate the receptacle having been opened (opening lands in Phase 9)
    repo = container.get_repos().receptacles
    receptacle = repo.get(created["id"])
    receptacle.state = ReceptacleState.OPENED
    repo.update(receptacle)

    response = client.get(reverse("receptacles"), {"state": "OPENED"})

    body = response.json()
    assert body["receptacles"][0]["reward_text"] == SECRET_TEXT


def test_non_secret_reward_text_is_visible_while_unopened(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"Value": 20, "Class": ["Freedom"]}])
    client.post(reverse("rewards"), {"text": "movie night"}, format="json")

    response = client.get(reverse("receptacles"), {"state": "IN_POOL"})

    assert response.json()["receptacles"][0]["reward_text"] == "movie night"


# --- listing ---


def test_get_receptacles_defaults_to_dropped_state(client):
    response = client.get(reverse("receptacles"))

    assert response.status_code == 200
    assert response.json()["receptacles"] == []


def test_get_receptacles_rejects_unknown_state(client):
    response = client.get(reverse("receptacles"), {"state": "NONSENSE"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATE"
