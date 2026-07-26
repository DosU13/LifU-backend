from datetime import timedelta

from django.urls import reverse
from rest_framework.test import APIClient

from services import container
from services.trial import get_trial_store


def _make_friend(client, name="alex") -> str:
    response = client.post(reverse("friends"), {"name": name}, format="json")
    assert response.status_code == 200, response.content
    return name


def _trial_client(anon_or_new_client, friend_name="alex") -> APIClient:
    session = anon_or_new_client.post(
        reverse("trial-session"), {"friend_name": friend_name}, format="json"
    )
    assert session.status_code == 200, session.content
    trial = APIClient()
    trial.credentials(HTTP_X_TRIAL_TOKEN=session.json()["token"])
    return trial


# --- friend links ---


def test_create_friend_link_returns_shareable_url(client):
    response = client.post(reverse("friends"), {"name": "Alex"}, format="json")

    assert response.status_code == 200
    assert response.json() == {"name": "alex", "url": "https://lifu.doslan.com/alex"}


def test_friend_names_must_be_slug_like(client):
    response = client.post(reverse("friends"), {"name": "not a slug!"}, format="json")
    assert response.status_code == 400


def test_duplicate_friend_name_is_rejected(client):
    client.post(reverse("friends"), {"name": "alex"}, format="json")
    response = client.post(reverse("friends"), {"name": "alex"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ALREADY_EXISTS"


def test_list_friend_links(client):
    client.post(reverse("friends"), {"name": "alex"}, format="json")
    client.post(reverse("friends"), {"name": "sam"}, format="json")

    body = client.get(reverse("friends")).json()

    assert {f["name"] for f in body["friends"]} == {"alex", "sam"}
    assert all(f["url"].startswith("https://lifu.doslan.com/") for f in body["friends"])


def test_public_friend_check_needs_no_auth(anon_client, client):
    _make_friend(client)

    assert anon_client.get(reverse("public-friend", args=["alex"])).json()["valid"] is True
    assert anon_client.get(reverse("public-friend", args=["nobody"])).json()["valid"] is False


# --- trial sessions ---


def test_trial_session_requires_a_known_friend_link(anon_client):
    response = anon_client.post(
        reverse("trial-session"), {"friend_name": "stranger"}, format="json"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_FRIEND"


def test_trial_token_grants_access_to_the_game(client, anon_client):
    _make_friend(client)
    trial = _trial_client(anon_client)

    response = trial.get(reverse("state"))

    assert response.status_code == 200
    assert trial.get(reverse("auth-session")).json() == {
        "authenticated": True,
        "is_trial": True,
    }


def test_unknown_trial_token_is_rejected():
    trial = APIClient()
    trial.credentials(HTTP_X_TRIAL_TOKEN="not-a-real-token")

    assert trial.get(reverse("state")).status_code == 401


def test_expired_trial_token_is_rejected(client, anon_client):
    _make_friend(client)
    session = anon_client.post(
        reverse("trial-session"), {"friend_name": "alex"}, format="json"
    ).json()

    store = get_trial_store()
    store._sessions[session["token"]].expires_at -= timedelta(hours=48)

    trial = APIClient()
    trial.credentials(HTTP_X_TRIAL_TOKEN=session["token"])
    assert trial.get(reverse("state")).status_code == 401


def test_trial_world_is_seeded_and_playable(client, anon_client):
    _make_friend(client)
    trial = _trial_client(anon_client)

    state = trial.get(reverse("state")).json()

    assert state["coins"] == 100
    assert state["stocks"]["FIRE_FRAGMENT"] == 5
    assert len(state["treasures"]) >= 1


def test_trial_cannot_manage_friend_links(client, anon_client):
    _make_friend(client)
    trial = _trial_client(anon_client)

    assert trial.get(reverse("friends")).status_code == 403
    assert trial.post(reverse("friends"), {"name": "x"}, format="json").status_code == 403


# --- isolation ---


def test_trial_changes_never_touch_the_owner_world(client, anon_client):
    _make_friend(client)
    owner_coins_before = client.get(reverse("state")).json()["coins"]
    trial = _trial_client(anon_client)

    trial.post(
        reverse("collectables-sell"),
        {"element": "FIRE", "rarity": "FRAGMENT", "count": 5},
        format="json",
    )

    assert trial.get(reverse("state")).json()["coins"] > 100
    assert client.get(reverse("state")).json()["coins"] == owner_coins_before


def test_trial_token_wins_over_an_owner_session_on_the_same_client(client, anon_client):
    """The owner opening their own friend link must get the sandbox, not the real save.

    `client` is signed in as the owner. Adding a trial token to that same
    client has to switch worlds — otherwise the ambient session cookie serves
    real data behind a "Trial" badge.
    """
    _make_friend(client)
    session = anon_client.post(
        reverse("trial-session"), {"friend_name": "alex"}, format="json"
    ).json()

    owner_state = client.get(reverse("state")).json()
    client.credentials(HTTP_X_TRIAL_TOKEN=session["token"])
    trial_state = client.get(reverse("state")).json()

    assert client.get(reverse("auth-session")).json()["is_trial"] is True
    assert trial_state["coins"] == 100  # the seeded sandbox, not the owner's wallet
    assert trial_state["coins"] != owner_state["coins"]


def test_an_invalid_trial_token_never_falls_back_to_the_owner_session(client):
    client.credentials(HTTP_X_TRIAL_TOKEN="not-a-real-token")
    assert client.get(reverse("state")).status_code == 401


def test_two_trial_tokens_are_isolated_from_each_other(client, anon_client):
    _make_friend(client, "alex")
    _make_friend(client, "sam")
    first = _trial_client(anon_client, "alex")
    second = _trial_client(anon_client, "sam")

    first.post(
        reverse("collectables-sell"),
        {"element": "FIRE", "rarity": "FRAGMENT", "count": 5},
        format="json",
    )

    assert first.get(reverse("state")).json()["coins"] > 100
    assert second.get(reverse("state")).json()["coins"] == 100


def test_trial_uses_no_groq_and_no_real_repositories(client, anon_client, monkeypatch):
    """A trial must not be able to spend the owner's Groq quota or touch their data."""
    _make_friend(client)

    def explode():
        raise AssertionError("trial reached the owner's AI client")

    trial = _trial_client(anon_client)
    monkeypatch.setattr(container, "get_ai_client", explode)
    monkeypatch.setattr(container, "get_repos", explode)

    # a full loop: task -> sell -> buy -> receptacles, all inside the sandbox
    task = trial.post(reverse("tasks"), {"text": "went for a run"}, format="json")
    assert task.status_code == 200
    assert (
        trial.post(
            reverse("collectables-sell"),
            {"element": "FIRE", "rarity": "FRAGMENT", "count": 1},
            format="json",
        ).status_code
        == 200
    )
    treasures = trial.get(reverse("treasures")).json()["treasures"]
    assert trial.post(reverse("treasure-buy", args=[treasures[0]["id"]])).status_code == 200
    assert trial.get(reverse("receptacles")).status_code == 200
