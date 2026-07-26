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


def test_build_repos_firebase_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        build_repos("firebase")


def test_build_repos_unknown_backend_raises():
    with pytest.raises(ValueError):
        build_repos("something-else")
