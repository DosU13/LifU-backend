from datetime import datetime, timezone

from core.entities import (
    FriendLink,
    GameMeta,
    GeneratedContent,
    Receptacle,
    Task,
    Treasure,
    Wallet,
    empty_collectable_stock,
)
from core.enums import (
    CollectableRarity,
    Element,
    GeneratedKind,
    ReceptacleRarity,
    ReceptacleState,
    TaskVirtue,
    Virtue,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_task_construction():
    task = Task(
        id="t1",
        text="Went for a run",
        created_at=NOW,
        value=10,
        virtues={TaskVirtue.WILLPOWER: 60, TaskVirtue.DISCIPLINE: 40},
        fragments_awarded={Element.FIRE: 3, Element.EARTH: 2},
    )
    assert task.value == 10
    assert task.fragments_awarded[Element.FIRE] == 3


def test_receptacle_construction_own_and_generated():
    own = Receptacle(
        id="r1",
        state=ReceptacleState.IN_POOL,
        virtue=Virtue.SERENITY,
        rarity=ReceptacleRarity.SAFE,
        value=42,
        is_generated=False,
        is_secret=False,
        friend_name=None,
        reward_text="A quiet afternoon by the lake",
        content=None,
        treasure_id=None,
        created_at=NOW,
    )
    assert own.opened_at is None
    assert own.reward_text is not None

    generated = Receptacle(
        id="r2",
        state=ReceptacleState.DROPPED,
        virtue=Virtue.VITALITY,
        rarity=ReceptacleRarity.POUCH,
        value=5,
        is_generated=True,
        is_secret=False,
        friend_name=None,
        reward_text=None,
        content=GeneratedContent(
            kind=GeneratedKind.QUOTE,
            title="Keep going",
            url="",
            author="Unknown",
            text="Small steps every day.",
        ),
        treasure_id=None,
        created_at=NOW,
    )
    assert generated.content.kind == GeneratedKind.QUOTE


def test_treasure_construction():
    t = Treasure(
        id="tr1",
        slot=0,
        receptacle_ids=["r1", "r2"],
        pity={ReceptacleRarity.VAULT: 0, ReceptacleRarity.SANCTUM: 0},
        created_at=NOW,
    )
    assert t.pity[ReceptacleRarity.SANCTUM] == 0
    assert len(t.receptacle_ids) == 2


def test_wallet_defaults_to_zero_coins():
    assert Wallet().coins == 0
    assert Wallet(coins=50).coins == 50


def test_friend_link_and_game_meta():
    link = FriendLink(name="alex", created_at=NOW)
    assert link.name == "alex"
    assert GameMeta().last_discard_date is None


def test_empty_collectable_stock_has_96_zeroed_entries():
    stock = empty_collectable_stock()
    assert len(stock) == 16 * 6
    assert all(v == 0 for v in stock.values())
    assert stock[(Element.FIRE, CollectableRarity.SHARD)] == 0
