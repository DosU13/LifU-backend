from dataclasses import dataclass

from repos.interfaces import (
    CollectableRepository,
    FriendLinkRepository,
    MetaRepository,
    ReceptacleRepository,
    TaskRepository,
    TreasureRepository,
    WalletRepository,
)
from repos.memory import (
    MemoryCollectableRepository,
    MemoryFriendLinkRepository,
    MemoryMetaRepository,
    MemoryReceptacleRepository,
    MemoryTaskRepository,
    MemoryTreasureRepository,
    MemoryWalletRepository,
)


@dataclass
class RepoBundle:
    tasks: TaskRepository
    collectables: CollectableRepository
    wallet: WalletRepository
    receptacles: ReceptacleRepository
    treasures: TreasureRepository
    friend_links: FriendLinkRepository
    meta: MetaRepository


def build_repos(backend: str) -> RepoBundle:
    """Build a fresh, independent set of repositories for the given backend."""
    if backend == "memory":
        return RepoBundle(
            tasks=MemoryTaskRepository(),
            collectables=MemoryCollectableRepository(),
            wallet=MemoryWalletRepository(),
            receptacles=MemoryReceptacleRepository(),
            treasures=MemoryTreasureRepository(),
            friend_links=MemoryFriendLinkRepository(),
            meta=MemoryMetaRepository(),
        )
    if backend == "firebase":
        raise NotImplementedError(
            "firebase backend lands in Phase 4 — use REPO_BACKEND=memory until then"
        )
    raise ValueError(f"unknown REPO_BACKEND: {backend!r}")
