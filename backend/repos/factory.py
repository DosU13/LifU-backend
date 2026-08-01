import os
from dataclasses import dataclass

from repos.firebase import (
    FirebaseCollectableRepository,
    FirebaseFriendLinkRepository,
    FirebaseMetaRepository,
    FirebaseReceptacleRepository,
    FirebaseTaskRepository,
    FirebaseTreasureRepository,
    FirebaseWalletRepository,
    get_firestore_client,
)
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
from repos.sqlite import (
    SQLiteCollectableRepository,
    SQLiteDatabase,
    SQLiteFriendLinkRepository,
    SQLiteMetaRepository,
    SQLiteReceptacleRepository,
    SQLiteTaskRepository,
    SQLiteTreasureRepository,
    SQLiteWalletRepository,
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
    if backend == "sqlite":
        db = SQLiteDatabase(os.environ.get("SQLITE_PATH", "data/lifu.db"))
        return RepoBundle(
            tasks=SQLiteTaskRepository(db),
            collectables=SQLiteCollectableRepository(db),
            wallet=SQLiteWalletRepository(db),
            receptacles=SQLiteReceptacleRepository(db),
            treasures=SQLiteTreasureRepository(db),
            friend_links=SQLiteFriendLinkRepository(db),
            meta=SQLiteMetaRepository(db),
        )
    if backend == "firebase":
        credentials_path = os.environ.get("FIREBASE_CREDENTIALS", "")
        if not credentials_path:
            raise RuntimeError("FIREBASE_CREDENTIALS must be set to use the firebase backend")
        db = get_firestore_client(credentials_path)
        return RepoBundle(
            tasks=FirebaseTaskRepository(db),
            collectables=FirebaseCollectableRepository(db),
            wallet=FirebaseWalletRepository(db),
            receptacles=FirebaseReceptacleRepository(db),
            treasures=FirebaseTreasureRepository(db),
            friend_links=FirebaseFriendLinkRepository(db),
            meta=FirebaseMetaRepository(db),
        )
    raise ValueError(f"unknown REPO_BACKEND: {backend!r}")
