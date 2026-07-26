import pytest

from services import container


def _clear(cached_fn) -> None:
    # Tests may monkeypatch get_ai_client with a plain lambda (no cache_clear);
    # monkeypatch's own teardown can run either before or after this fixture's,
    # so tolerate whichever function object is currently in place.
    clear = getattr(cached_fn, "cache_clear", None)
    if clear is not None:
        clear()


@pytest.fixture(autouse=True)
def _reset_container_caches():
    """Container singletons (memory repos, AI client) must not leak between tests."""
    _clear(container.get_repos)
    _clear(container.get_ai_client)
    yield
    _clear(container.get_repos)
    _clear(container.get_ai_client)
