from abc import ABC, abstractmethod
from datetime import date, datetime

from core.entities import CollectableStock, FriendLink, Receptacle, Task, Treasure
from core.enums import CollectableRarity, Element, ReceptacleState


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> Task:
        """Persist a task (assigning an id if the given task has none) and return it."""

    @abstractmethod
    def list_since(self, since: datetime) -> list[Task]:
        """Tasks created at or after `since`, ordered by created_at ascending."""


class CollectableRepository(ABC):
    @abstractmethod
    def get_all(self) -> CollectableStock:
        """All 96 (element, rarity) counters."""

    @abstractmethod
    def adjust(self, deltas: dict[tuple[Element, CollectableRarity], int]) -> None:
        """Apply every delta atomically. Raises InsufficientCollectables — with none

        of the deltas applied — if any resulting count would go negative.
        """


class WalletRepository(ABC):
    @abstractmethod
    def get_coins(self) -> int: ...

    @abstractmethod
    def adjust(self, delta: int) -> int:
        """Apply delta atomically and return the new balance. Raises

        InsufficientCoins — balance left unchanged — if the result would be negative.
        """


class ReceptacleRepository(ABC):
    @abstractmethod
    def add(self, receptacle: Receptacle) -> Receptacle:
        """Persist a receptacle (assigning an id if it has none) and return it."""

    @abstractmethod
    def get(self, receptacle_id: str) -> Receptacle:
        """Raises NotFound if no receptacle with this id exists."""

    @abstractmethod
    def get_many(self, receptacle_ids: list[str]) -> list[Receptacle]:
        """Fetch several receptacles in one round trip.

        Returns them in the order requested, silently skipping ids that no
        longer exist — callers use this for display, where a vanished
        receptacle should simply not appear rather than fail the whole read.
        """

    @abstractmethod
    def update(self, receptacle: Receptacle) -> None:
        """Raises NotFound if no receptacle with this id exists yet."""

    @abstractmethod
    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]: ...

    @abstractmethod
    def list_non_generated(self) -> list[Receptacle]:
        """Every non-generated receptacle regardless of state — the input to

        rarity recalculation (ARCHITECTURE §7.4), which must see opened ones too.
        """


class TreasureRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Treasure]:
        """The current treasures (normally at most TREASURE_COUNT)."""

    @abstractmethod
    def save(self, treasure: Treasure) -> None:
        """Insert or overwrite by id."""

    @abstractmethod
    def delete(self, treasure_id: str) -> None:
        """No-op if the id doesn't exist."""


class FriendLinkRepository(ABC):
    @abstractmethod
    def add(self, name: str) -> FriendLink:
        """Raises AlreadyExists if a friend link with this name already exists."""

    @abstractmethod
    def get(self, name: str) -> FriendLink | None: ...

    @abstractmethod
    def list_all(self) -> list[FriendLink]: ...


class MetaRepository(ABC):
    @abstractmethod
    def get_last_discard_date(self) -> date | None: ...

    @abstractmethod
    def set_last_discard_date(self, d: date) -> None: ...
