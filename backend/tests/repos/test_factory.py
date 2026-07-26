import os

import pytest

from repos.factory import RepoBundle, build_repos
from repos.memory import MemoryTaskRepository


def test_build_repos_memory_returns_full_bundle():
    bundle = build_repos("memory")
    assert isinstance(bundle, RepoBundle)
    assert isinstance(bundle.tasks, MemoryTaskRepository)


def test_build_repos_memory_returns_independent_bundles():
    a = build_repos("memory")
    b = build_repos("memory")
    a.wallet.adjust(50)
    assert b.wallet.get_coins() == 0


def test_build_repos_firebase_without_credentials_raises(monkeypatch):
    monkeypatch.delenv("FIREBASE_CREDENTIALS", raising=False)
    with pytest.raises(RuntimeError):
        build_repos("firebase")


@pytest.mark.skipif(
    not os.environ.get("FIREBASE_CREDENTIALS"),
    reason="FIREBASE_CREDENTIALS not set — skipping live Firebase check",
)
def test_build_repos_firebase_returns_full_bundle_live():
    from repos.firebase import FirebaseTaskRepository

    bundle = build_repos("firebase")
    assert isinstance(bundle, RepoBundle)
    assert isinstance(bundle.tasks, FirebaseTaskRepository)


def test_build_repos_unknown_backend_raises():
    with pytest.raises(ValueError):
        build_repos("something-else")
