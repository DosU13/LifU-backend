import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from providers.fallback import FallbackContentProvider
from services import container
from services.trial import get_trial_store

OWNER_PASSWORD = "test-owner-password"


def _clear(cached_fn) -> None:
    # Tests may monkeypatch a container factory with a plain lambda (no
    # cache_clear); monkeypatch's teardown can run either before or after this
    # fixture's, so tolerate whichever function object is currently in place.
    clear = getattr(cached_fn, "cache_clear", None)
    if clear is not None:
        clear()


def _clear_all() -> None:
    _clear(container.get_repos)
    _clear(container.get_ai_client)
    _clear(container.get_rng)
    _clear(container.get_content_provider)
    get_trial_store().clear()


@pytest.fixture(autouse=True)
def _reset_state(settings):
    """No game state, trial session, or cached collaborator leaks between tests.

    Also clears Django's cache: DRF throttling (see GiftThrottle) counts
    requests there, keyed by client IP, and the Django test client always
    uses the same IP -- without this, unrelated tests hitting a throttled
    view would accumulate against one shared counter and eventually start
    failing with 429s that have nothing to do with what they're testing.
    """
    settings.OWNER_PASSWORD = OWNER_PASSWORD
    settings.REPO_BACKEND = "memory"
    _clear_all()
    cache.clear()
    yield
    _clear_all()
    cache.clear()


@pytest.fixture(autouse=True)
def _no_live_content(monkeypatch):
    """Keep the API suite offline.

    The real container builds a chain of live HTTP content sources; a treasure
    buy that drops a Pouch or Sack would otherwise call out to the network.
    """
    monkeypatch.setattr(
        container,
        "get_content_provider",
        lambda: FallbackContentProvider(rng=container.get_rng()),
    )


@pytest.fixture
def anon_client() -> APIClient:
    """No session, no trial token — should be refused by every game endpoint."""
    return APIClient()


@pytest.fixture
def client(anon_client) -> APIClient:
    """Signed in as the owner."""
    response = anon_client.post(
        "/api/auth/login", {"password": OWNER_PASSWORD}, format="json"
    )
    assert response.status_code == 200, response.content
    return anon_client
