import pytest
from django.urls import reverse

from tests.api.conftest import OWNER_PASSWORD

# Every game endpoint, as (url name, method, kwargs) — used to prove the
# whole surface is closed to anonymous callers.
GAME_ENDPOINTS = [
    ("tasks", "get", {}),
    ("tasks", "post", {}),
    ("stats", "get", {}),
    ("collectables", "get", {}),
    ("collectables-merge", "post", {}),
    ("collectables-harmony", "post", {}),
    ("collectables-combine", "post", {}),
    ("collectables-sell", "post", {}),
    ("rewards", "post", {}),
    ("receptacles", "get", {}),
    ("receptacle-open", "post", {"args": ["some-id"]}),
    ("treasures", "get", {}),
    ("treasure-buy", "post", {"args": ["some-id"]}),
    ("treasure-discard", "post", {"args": ["some-id"]}),
    ("state", "get", {}),
    ("friends", "get", {}),
    ("friends", "post", {}),
]


@pytest.mark.parametrize(("url_name", "method", "kwargs"), GAME_ENDPOINTS)
def test_game_endpoints_reject_anonymous_callers(anon_client, url_name, method, kwargs):
    url = reverse(url_name, **kwargs)
    response = getattr(anon_client, method)(url)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_login_with_correct_password(anon_client):
    response = anon_client.post(
        reverse("auth-login"), {"password": OWNER_PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_login_with_wrong_password_returns_401(anon_client):
    response = anon_client.post(
        reverse("auth-login"), {"password": "not-the-password"}, format="json"
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_PASSWORD"

    # and the session must not have been granted
    assert anon_client.get(reverse("state")).status_code == 401


def test_login_is_refused_when_no_owner_password_is_configured(anon_client, settings):
    """An unset OWNER_PASSWORD must lock the game, not open it to anything."""
    settings.OWNER_PASSWORD = ""
    response = anon_client.post(reverse("auth-login"), {"password": "guess"}, format="json")

    assert response.status_code == 401
    assert anon_client.get(reverse("state")).status_code == 401


def test_logout_ends_the_session(client):
    assert client.get(reverse("state")).status_code == 200

    assert client.post(reverse("auth-logout")).status_code == 200

    assert client.get(reverse("state")).status_code == 401


def test_session_endpoint_reports_auth_state(anon_client):
    before = anon_client.get(reverse("auth-session")).json()
    assert before == {"authenticated": False, "is_trial": False}

    anon_client.post(reverse("auth-login"), {"password": OWNER_PASSWORD}, format="json")

    after = anon_client.get(reverse("auth-session")).json()
    assert after == {"authenticated": True, "is_trial": False}


def test_health_stays_public(anon_client):
    assert anon_client.get(reverse("health")).status_code == 200
