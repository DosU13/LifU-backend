import threading
import uuid
from copy import deepcopy
from datetime import date, datetime, timezone

from core.entities import (
    CollectableStock,
    FriendLink,
    GameMeta,
    Receptacle,
    Task,
    Treasure,
    Wallet,
    empty_collectable_stock,
)
from core.enums import CollectableRarity, Element, ReceptacleState
from core.errors import AlreadyExists, InsufficientCoins, InsufficientCollectables, NotFound
from repos.interfaces import (
    CollectableRepository,
    FriendLinkRepository,
    MetaRepository,
    ReceptacleRepository,
    TaskRepository,
    TreasureRepository,
    WalletRepository,
)


def _new_id() -> str:
    return uuid.uuid4().hex


class MemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def add(self, task: Task) -> Task:
        with self._lock:
            stored = deepcopy(task)
            if not stored.id:
                stored.id = _new_id()
            self._tasks[stored.id] = stored
            return deepcopy(stored)

    def list_since(self, since: datetime) -> list[Task]:
        with self._lock:
            matches = [deepcopy(t) for t in self._tasks.values() if t.created_at >= since]
        return sorted(matches, key=lambda t: t.created_at)


class MemoryCollectableRepository(CollectableRepository):
    def __init__(self) -> None:
        self._stock: CollectableStock = empty_collectable_stock()
        self._lock = threading.Lock()

    def get_all(self) -> CollectableStock:
        with self._lock:
            return dict(self._stock)

    def adjust(self, deltas: dict[tuple[Element, CollectableRarity], int]) -> None:
        with self._lock:
            proposed = dict(self._stock)
            for key, delta in deltas.items():
                proposed[key] = proposed.get(key, 0) + delta
            negative = sorted(k for k, v in proposed.items() if v < 0)
            if negative:
                names = ", ".join(f"{e.value}_{r.name}" for e, r in negative)
                raise InsufficientCollectables(f"insufficient stock for: {names}")
            self._stock = proposed


class MemoryWalletRepository(WalletRepository):
    def __init__(self) -> None:
        self._wallet = Wallet(coins=0)
        self._lock = threading.Lock()

    def get_coins(self) -> int:
        with self._lock:
            return self._wallet.coins

    def adjust(self, delta: int) -> int:
        with self._lock:
            new_balance = self._wallet.coins + delta
            if new_balance < 0:
                raise InsufficientCoins(
                    f"cannot adjust coins by {delta}: balance would go negative"
                )
            self._wallet.coins = new_balance
            return new_balance


class MemoryReceptacleRepository(ReceptacleRepository):
    def __init__(self) -> None:
        self._receptacles: dict[str, Receptacle] = {}
        self._lock = threading.Lock()

    def add(self, receptacle: Receptacle) -> Receptacle:
        with self._lock:
            stored = deepcopy(receptacle)
            if not stored.id:
                stored.id = _new_id()
            self._receptacles[stored.id] = stored
            return deepcopy(stored)

    def get(self, receptacle_id: str) -> Receptacle:
        with self._lock:
            try:
                return deepcopy(self._receptacles[receptacle_id])
            except KeyError as exc:
                raise NotFound(f"no receptacle with id {receptacle_id}") from exc

    def update(self, receptacle: Receptacle) -> None:
        with self._lock:
            if receptacle.id not in self._receptacles:
                raise NotFound(f"no receptacle with id {receptacle.id}")
            self._receptacles[receptacle.id] = deepcopy(receptacle)

    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]:
        with self._lock:
            return [deepcopy(r) for r in self._receptacles.values() if r.state == state]

    def list_non_generated(self) -> list[Receptacle]:
        with self._lock:
            return [deepcopy(r) for r in self._receptacles.values() if not r.is_generated]


class MemoryTreasureRepository(TreasureRepository):
    def __init__(self) -> None:
        self._treasures: dict[str, Treasure] = {}
        self._lock = threading.Lock()

    def get_all(self) -> list[Treasure]:
        with self._lock:
            return [deepcopy(t) for t in self._treasures.values()]

    def save(self, treasure: Treasure) -> None:
        with self._lock:
            self._treasures[treasure.id] = deepcopy(treasure)

    def delete(self, treasure_id: str) -> None:
        with self._lock:
            self._treasures.pop(treasure_id, None)


class MemoryFriendLinkRepository(FriendLinkRepository):
    def __init__(self) -> None:
        self._links: dict[str, FriendLink] = {}
        self._lock = threading.Lock()

    def add(self, name: str) -> FriendLink:
        with self._lock:
            if name in self._links:
                raise AlreadyExists(f"friend link '{name}' already exists")
            link = FriendLink(name=name, created_at=datetime.now(timezone.utc))
            self._links[name] = link
            return deepcopy(link)

    def get(self, name: str) -> FriendLink | None:
        with self._lock:
            link = self._links.get(name)
            return deepcopy(link) if link else None

    def list_all(self) -> list[FriendLink]:
        with self._lock:
            return [deepcopy(link) for link in self._links.values()]


class MemoryMetaRepository(MetaRepository):
    def __init__(self) -> None:
        self._meta = GameMeta()
        self._lock = threading.Lock()

    def get_last_discard_date(self) -> date | None:
        with self._lock:
            return self._meta.last_discard_date

    def set_last_discard_date(self, d: date) -> None:
        with self._lock:
            self._meta.last_discard_date = d
