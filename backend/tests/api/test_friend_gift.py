import json

from django.urls import reverse

from aiclients.fake import FakeAIClient
from core.enums import ReceptacleState
from services import container


def _use_fake_ai(monkeypatch, responses):
    fake = FakeAIClient(responses)
    monkeypatch.setattr(container, "get_ai_client", lambda: fake)
    return fake


def _make_friend(client, name="alex") -> str:
    response = client.post(reverse("friends"), {"name": name}, format="json")
    assert response.status_code == 200, response.content
    return name


SECRET_TEXT = "a weekend trip somewhere you have never been"


def test_public_friend_check_reports_has_gifted(anon_client, client, monkeypatch):
    _make_friend(client)
    _use_fake_ai(monkeypatch, [{"Value": 60, "Class": ["Freedom"]}])

    before = anon_client.get(reverse("public-friend", args=["alex"])).json()
    assert before == {"valid": True, "name": "alex", "has_gifted": False}

    anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": SECRET_TEXT}, format="json"
    )

    after = anon_client.get(reverse("public-friend", args=["alex"])).json()
    assert after["has_gifted"] is True


def test_gift_seals_a_secret_reward_hidden_from_the_owner(anon_client, client, monkeypatch):
    _make_friend(client)
    _use_fake_ai(monkeypatch, [{"Value": 60, "Class": ["Freedom"]}])

    response = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": SECRET_TEXT}, format="json"
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    # nothing about the reward comes back to the friend either
    assert SECRET_TEXT not in json.dumps(response.json())

    rewards = client.get(reverse("rewards")).json()["rewards"]
    assert len(rewards) == 1
    assert rewards[0]["is_secret"] is True
    assert rewards[0]["friend_name"] == "alex"
    assert rewards[0]["text"] is None  # hidden from the owner until opened

    receptacle = container.get_repos().receptacles.list_non_generated()[0]
    assert receptacle.reward_text == SECRET_TEXT
    assert receptacle.state is ReceptacleState.IN_POOL


def test_gift_unknown_friend_returns_404(anon_client):
    response = anon_client.post(
        reverse("public-friend-gift", args=["nobody"]), {"text": "text"}, format="json"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_FRIEND"


def test_gift_blocks_a_second_submission_on_the_same_link(anon_client, client, monkeypatch):
    _make_friend(client)
    _use_fake_ai(monkeypatch, [{"Value": 60, "Class": ["Freedom"]}] * 2)

    first = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": SECRET_TEXT}, format="json"
    )
    assert first.status_code == 200

    second = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": "a second gift"}, format="json"
    )
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "ALREADY_GIFTED"

    # the second attempt must not have created anything
    assert len(container.get_repos().receptacles.list_non_generated()) == 1


def test_gift_blocks_second_submission_even_after_an_owner_composed_one(
    anon_client, client, monkeypatch
):
    """One gift per friend name, regardless of which channel created the first one."""
    _make_friend(client)
    _use_fake_ai(monkeypatch, [{"Value": 60, "Class": ["Freedom"]}])
    client.post(
        reverse("rewards"),
        {"text": "owner-entered on alex's behalf", "is_secret": True, "friend_name": "alex"},
        format="json",
    )

    response = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": SECRET_TEXT}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ALREADY_GIFTED"


def test_gift_blank_text_returns_400(anon_client, client):
    _make_friend(client)

    response = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": ""}, format="json"
    )

    assert response.status_code == 400


def test_gift_ai_failure_returns_502(anon_client, client, monkeypatch):
    _make_friend(client)
    _use_fake_ai(monkeypatch, [{"bad": 1}, {"bad": 1}, {"bad": 1}])

    response = anon_client.post(
        reverse("public-friend-gift", args=["alex"]), {"text": SECRET_TEXT}, format="json"
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID"
    # nothing persisted on failure
    assert container.get_repos().receptacles.list_non_generated() == []
