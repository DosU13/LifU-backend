import pytest

from providers.fallback import FallbackContentProvider
from services import container


def _clear(cached_fn) -> None:
    # Tests may monkeypatch get_ai_client with a plain lambda (no cache_clear);
    # monkeypatch's own teardown can run either before or after this fixture's,
    # so tolerate whichever function object is currently in place.
    clear = getattr(cached_fn, "cache_clear", None)
    if clear is not None:
        clear()


def _clear_all() -> None:
    _clear(container.get_repos)
    _clear(container.get_ai_client)
    _clear(container.get_rng)
    _clear(container.get_content_provider)


@pytest.fixture(autouse=True)
def _reset_container_caches():
    """Container singletons must not leak between tests."""
    _clear_all()
    yield
    _clear_all()


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
