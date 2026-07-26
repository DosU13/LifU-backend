from dataclasses import dataclass
from datetime import date, datetime

from core.enums import (
    CollectableRarity,
    Element,
    GeneratedKind,
    ReceptacleRarity,
    ReceptacleState,
    TaskVirtue,
    Virtue,
)


@dataclass
class Task:
    id: str
    text: str
    created_at: datetime
    value: int
    virtues: dict[TaskVirtue, int]
    fragments_awarded: dict[Element, int]


@dataclass
class GeneratedContent:
    kind: GeneratedKind
    title: str
    url: str
    author: str
    text: str


@dataclass
class Receptacle:
    id: str
    state: ReceptacleState
    virtue: Virtue
    rarity: ReceptacleRarity
    value: int
    is_generated: bool
    is_secret: bool
    friend_name: str | None
    reward_text: str | None
    content: GeneratedContent | None
    treasure_id: str | None
    created_at: datetime
    opened_at: datetime | None = None


@dataclass
class Treasure:
    id: str
    slot: int
    receptacle_ids: list[str]
    pity: dict[ReceptacleRarity, int]
    created_at: datetime
    # Fixed at generation from the treasure's starting contents. Never changes
    # for this treasure's lifetime, so emptying it does not make it cheaper.
    price: int = 1


@dataclass
class Wallet:
    coins: int = 0


@dataclass
class FriendLink:
    name: str
    created_at: datetime


@dataclass
class GameMeta:
    last_discard_date: date | None = None


# Conceptually dict[(Element, CollectableRarity), int]; stored in Firestore as
# one document with 96 counter fields (e.g. "FIRE_SHARD") — see ARCHITECTURE §6.
CollectableStock = dict[tuple[Element, CollectableRarity], int]


def empty_collectable_stock() -> CollectableStock:
    return {(e, r): 0 for e in Element for r in CollectableRarity}
