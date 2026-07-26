from datetime import date, datetime, timezone

import pytest

from core.constants import PITY_THRESHOLDS
from core.entities import GeneratedContent, Receptacle
from core.enums import GeneratedKind, ReceptacleRarity, ReceptacleState, Virtue
from core.errors import DiscardAlreadyUsed, InsufficientCoins, NotFound
from repos.memory import (
    MemoryMetaRepository,
    MemoryReceptacleRepository,
    MemoryTreasureRepository,
    MemoryWalletRepository,
)
from services.rarity_service import RarityService
from services.treasure_service import TreasureService

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

SANCTUM = ReceptacleRarity.SANCTUM
VAULT = ReceptacleRarity.VAULT
SAFE = ReceptacleRarity.SAFE
CHEST = ReceptacleRarity.CHEST
SACK = ReceptacleRarity.SACK
POUCH = ReceptacleRarity.POUCH


class _ScriptedRng:
    """Deterministic stand-in: `random()` pops a scripted value; the rest are simple."""

    def __init__(self, randoms=(), randints=(), choice_index=0):
        self.randoms = list(randoms)
        self.randints = list(randints)
        self.choice_index = choice_index

    def random(self) -> float:
        return self.randoms.pop(0) if self.randoms else 0.999

    def randint(self, a: int, b: int) -> int:
        return self.randints.pop(0) if self.randints else a

    def choice(self, seq):
        return seq[self.choice_index % len(seq)]

    def shuffle(self, seq) -> None:
        pass  # deterministic: leave order untouched


class _StubContent:
    def fetch(self, rarity: ReceptacleRarity) -> GeneratedContent:
        return GeneratedContent(
            kind=GeneratedKind.QUOTE, title="t", url="", author="a", text="text"
        )


def _receptacle(value: int, rarity: ReceptacleRarity, state=ReceptacleState.IN_POOL) -> Receptacle:
    return Receptacle(
        id="",
        state=state,
        virtue=Virtue.SERENITY,
        rarity=rarity,
        value=value,
        is_generated=False,
        is_secret=False,
        friend_name=None,
        reward_text="reward",
        content=None,
        treasure_id=None,
        created_at=NOW,
    )


def _build(rng=None, coins=1000, now=NOW):
    receptacles = MemoryReceptacleRepository()
    treasures = MemoryTreasureRepository()
    wallet = MemoryWalletRepository()
    meta = MemoryMetaRepository()
    if coins:
        wallet.adjust(coins)
    service = TreasureService(
        treasures=treasures,
        receptacles=receptacles,
        wallet=wallet,
        meta=meta,
        rarity=RarityService(receptacles),
        content=_StubContent(),
        rng=rng or _ScriptedRng(),
        timezone_name="UTC",
        now=lambda: now,
    )
    return service, receptacles, treasures, wallet, meta


def _treasure_with(service, receptacles, treasures, specs: list[tuple[int, ReceptacleRarity]]):
    """Build a treasure holding exactly the given (value, rarity) receptacles."""
    ids = []
    for value, rarity in specs:
        stored = receptacles.add(_receptacle(value, rarity, ReceptacleState.IN_TREASURE))
        ids.append(stored.id)
    from core.entities import Treasure

    treasure = Treasure(
        id="t1",
        slot=0,
        receptacle_ids=ids,
        pity=dict.fromkeys(PITY_THRESHOLDS, 0),
        created_at=NOW,
    )
    for rid in ids:
        r = receptacles.get(rid)
        r.treasure_id = treasure.id
        receptacles.update(r)
    treasures.save(treasure)
    return treasure


# --- generation ---


def test_generate_draws_between_5_and_10_from_pool():
    service, receptacles, treasures, _, _ = _build(rng=_ScriptedRng(randints=[7]))
    for i in range(20):
        receptacles.add(_receptacle(10 + i, CHEST))

    treasure = service.generate(slot=0)

    assert len(treasure.receptacle_ids) == 7
    for rid in treasure.receptacle_ids:
        stored = receptacles.get(rid)
        assert stored.state is ReceptacleState.IN_TREASURE
        assert stored.treasure_id == treasure.id


def test_generate_clamps_to_pool_size_when_pool_is_small():
    service, receptacles, _, _, _ = _build(rng=_ScriptedRng(randints=[10]))
    for _ in range(3):
        receptacles.add(_receptacle(10, CHEST))

    treasure = service.generate(slot=0)

    assert len(treasure.receptacle_ids) == 3


def test_generate_returns_none_when_pool_is_empty():
    service, _, treasures, _, _ = _build()
    assert service.generate(slot=0) is None
    assert treasures.get_all() == []


def test_generate_spreads_across_rarities():
    service, receptacles, _, _, _ = _build(rng=_ScriptedRng(randints=[6]))
    for _ in range(5):
        receptacles.add(_receptacle(10, CHEST))
    for _ in range(5):
        receptacles.add(_receptacle(50, SAFE))

    treasure = service.generate(slot=0)
    rarities = [receptacles.get(rid).rarity for rid in treasure.receptacle_ids]

    # round-robin across groups means both rarities must be represented
    assert CHEST in rarities
    assert SAFE in rarities


def test_refill_empty_slots_creates_three_treasures():
    service, receptacles, treasures, _, _ = _build(rng=_ScriptedRng(randints=[5, 5, 5]))
    for i in range(30):
        receptacles.add(_receptacle(10 + i, CHEST))

    service.refill_empty_slots()

    assert {t.slot for t in treasures.get_all()} == {0, 1, 2}


def test_receptacle_belongs_to_only_one_treasure():
    service, receptacles, treasures, _, _ = _build(rng=_ScriptedRng(randints=[5, 5, 5]))
    for i in range(12):
        receptacles.add(_receptacle(10 + i, CHEST))

    service.refill_empty_slots()

    all_ids = [rid for t in treasures.get_all() for rid in t.receptacle_ids]
    assert len(all_ids) == len(set(all_ids))


# --- price ---


def test_price_is_ceiling_of_mean_value():
    service, receptacles, treasures, _, _ = _build()
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST), (21, SAFE)])

    assert service.price(treasure) == 16  # ceil(15.5)


def test_price_recomputed_as_treasure_empties():
    # sanctum/vault/safe rolls miss, chest roll hits
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.0])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST), (100, CHEST)])
    assert service.price(treasure) == 55

    service.buy(treasure.id)
    remaining = service._get_treasure(treasure.id)

    assert len(remaining.receptacle_ids) == 1
    assert service.price(remaining) in (10, 100)  # now just the survivor's value


# --- buy: roll order and fall-through ---


def test_buy_rolls_rarest_first():
    # The Sanctum roll hits first, so a Sanctum is won even though lesser tiers follow.
    rng = _ScriptedRng(randoms=[0.0])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(
        service, receptacles, treasures, [(90, SANCTUM), (50, VAULT), (10, CHEST)]
    )

    result = service.buy(treasure.id)

    assert result.dropped_rarity is SANCTUM
    assert result.receptacle.value == 90  # the Sanctum-slot receptacle is the one that left
    assert result.receptacle.state is ReceptacleState.DROPPED


def test_dropped_receptacle_may_be_relabelled_by_recalculation():
    """A won rarity is reported as-dropped even though recalculation may re-label it.

    With only 3 non-generated receptacles in existence, apportion(3) allows no
    Sanctum at all, so the receptacle that dropped as a Sanctum immediately
    becomes a Safe. That is per ARCHITECTURE §2 (rarity stays mutable until opened).
    """
    rng = _ScriptedRng(randoms=[0.0])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(
        service, receptacles, treasures, [(90, SANCTUM), (50, VAULT), (10, CHEST)]
    )

    result = service.buy(treasure.id)

    assert result.dropped_rarity is SANCTUM
    assert result.receptacle.rarity is SAFE  # re-labelled: only 3 receptacles exist


def test_buy_falls_through_when_rolled_tier_is_absent():
    """A hit on a tier the treasure doesn't hold must fall through, not drop nothing."""
    # every tier "hits" (0.0), but the treasure only holds a Chest
    rng = _ScriptedRng(randoms=[0.0, 0.0, 0.0, 0.0])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])

    result = service.buy(treasure.id)

    assert result.dropped_rarity is CHEST


def test_buy_falls_back_to_pouch_when_all_tiers_miss():
    # all four real tiers miss, then the Sack roll misses too -> Pouch
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.9, 0.9], randints=[7])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])

    result = service.buy(treasure.id)

    assert result.receptacle.rarity is POUCH
    assert result.receptacle.is_generated is True
    assert result.receptacle.state is ReceptacleState.DROPPED
    assert result.receptacle.content is not None
    # the treasure keeps its real receptacle
    assert len(service._get_treasure(treasure.id).receptacle_ids) == 1


def test_buy_falls_back_to_sack_when_sack_roll_hits():
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.9, 0.0], randints=[20])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])

    result = service.buy(treasure.id)

    assert result.receptacle.rarity is SACK
    assert result.receptacle.is_generated is True


def test_buy_charges_price_and_returns_balance():
    rng = _ScriptedRng(randoms=[0.999, 0.999, 0.999, 0.0])
    service, receptacles, treasures, wallet, _ = _build(rng=rng, coins=100)
    treasure = _treasure_with(service, receptacles, treasures, [(40, CHEST), (40, CHEST)])

    result = service.buy(treasure.id)

    assert result.price_paid == 40
    assert result.coins == 60
    assert wallet.get_coins() == 60


def test_buy_without_enough_coins_raises_and_drops_nothing():
    service, receptacles, treasures, wallet, _ = _build(coins=5)
    treasure = _treasure_with(service, receptacles, treasures, [(50, CHEST)])

    with pytest.raises(InsufficientCoins):
        service.buy(treasure.id)

    assert wallet.get_coins() == 5
    assert len(service._get_treasure(treasure.id).receptacle_ids) == 1


def test_buy_unknown_treasure_raises_not_found():
    service, _, _, _, _ = _build()
    with pytest.raises(NotFound):
        service.buy("nope")


# --- pity ---


def test_pity_counters_increment_on_every_buy():
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.9, 0.9], randints=[5])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])

    result = service.buy(treasure.id)

    assert result.pity[VAULT] == 1
    assert result.pity[SANCTUM] == 1


def test_vault_pity_fires_at_threshold():
    rng = _ScriptedRng(randoms=[0.9] * 10)
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(50, VAULT), (10, CHEST)])
    treasure.pity[VAULT] = PITY_THRESHOLDS[VAULT]
    treasures.save(treasure)

    result = service.buy(treasure.id)

    assert result.was_pity is True
    assert result.dropped_rarity is VAULT
    assert result.pity[VAULT] == 0  # reset by its own drop


def test_sanctum_pity_checked_before_vault_pity():
    rng = _ScriptedRng(randoms=[0.9] * 10)
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(90, SANCTUM), (50, VAULT)])
    treasure.pity[VAULT] = PITY_THRESHOLDS[VAULT]
    treasure.pity[SANCTUM] = PITY_THRESHOLDS[SANCTUM]
    treasures.save(treasure)

    result = service.buy(treasure.id)

    assert result.dropped_rarity is SANCTUM
    assert result.pity[SANCTUM] == 0
    assert result.pity[VAULT] == PITY_THRESHOLDS[VAULT] + 1  # kept counting


def test_unfulfillable_pity_keeps_counting_then_fires_when_possible():
    """Pity past its threshold with no such rarity present must not be lost."""
    rng = _ScriptedRng(randoms=[0.9] * 20, randints=[5, 5])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST), (10, CHEST)])
    treasure.pity[VAULT] = PITY_THRESHOLDS[VAULT]
    treasures.save(treasure)

    # no Vault in the treasure -> pity can't fire, counter climbs
    first = service.buy(treasure.id)
    assert first.dropped_rarity is not VAULT
    assert first.pity[VAULT] == PITY_THRESHOLDS[VAULT] + 1

    # now add a Vault to the treasure; the next buy must pay the debt
    current = service._get_treasure(treasure.id)
    vault = receptacles.add(_receptacle(70, VAULT, ReceptacleState.IN_TREASURE))
    current.receptacle_ids.append(vault.id)
    treasures.save(current)

    second = service.buy(treasure.id)
    assert second.was_pity is True
    assert second.dropped_rarity is VAULT
    assert second.pity[VAULT] == 0


def test_pity_dies_with_the_treasure():
    rng = _ScriptedRng(randoms=[0.9] * 20, randints=[5])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    treasure.pity[VAULT] = 20
    treasures.save(treasure)
    # give the pool something so a replacement treasure can be generated
    for _ in range(5):
        receptacles.add(_receptacle(10, CHEST))

    # emptying the treasure destroys it and generates a fresh one
    rng.randoms = [0.9, 0.9, 0.9, 0.0]  # only the Chest tier hits
    result = service.buy(treasure.id)

    assert result.treasure_gone is True
    replacement = [t for t in treasures.get_all() if t.slot == 0][0]
    assert replacement.id != treasure.id
    assert replacement.pity[VAULT] == 0  # counters do not migrate


# --- regeneration ---


def test_emptied_treasure_is_deleted_and_regenerated():
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.0], randints=[5])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    for _ in range(5):
        receptacles.add(_receptacle(20, CHEST))

    result = service.buy(treasure.id)

    assert result.treasure_gone is True
    remaining = treasures.get_all()
    assert len(remaining) == 1
    assert remaining[0].id != treasure.id
    assert remaining[0].slot == 0


# --- discard ---


def test_discard_returns_contents_to_pool_and_regenerates():
    service, receptacles, treasures, _, meta = _build(rng=_ScriptedRng(randints=[5]))
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST), (20, SAFE)])

    service.discard(treasure.id)

    for rid in treasure.receptacle_ids:
        stored = receptacles.get(rid)
        assert stored.state in (ReceptacleState.IN_POOL, ReceptacleState.IN_TREASURE)
        # they went back to the pool (and may have been redrawn into the new treasure)
    assert meta.get_last_discard_date() == NOW.date()


def test_discard_twice_in_one_day_is_rejected():
    service, receptacles, treasures, _, _ = _build(rng=_ScriptedRng(randints=[5]))
    first = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    service.discard(first.id)

    second = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    with pytest.raises(DiscardAlreadyUsed):
        service.discard(second.id)


def test_discard_allowed_again_the_next_day():
    service, receptacles, treasures, _, meta = _build(rng=_ScriptedRng(randints=[5]))
    meta.set_last_discard_date(date(2026, 1, 14))  # yesterday relative to NOW
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])

    service.discard(treasure.id)  # must not raise

    assert meta.get_last_discard_date() == NOW.date()


def test_discard_day_boundary_uses_configured_timezone():
    """23:00 UTC is already the next local day in Tokyo (UTC+9)."""
    receptacles = MemoryReceptacleRepository()
    treasures = MemoryTreasureRepository()
    meta = MemoryMetaRepository()
    late_utc = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)  # = Jan 16 08:00 JST
    service = TreasureService(
        treasures=treasures,
        receptacles=receptacles,
        wallet=MemoryWalletRepository(),
        meta=meta,
        rarity=RarityService(receptacles),
        content=_StubContent(),
        rng=_ScriptedRng(randints=[5]),
        timezone_name="Asia/Tokyo",
        now=lambda: late_utc,
    )
    meta.set_last_discard_date(date(2026, 1, 15))  # used "today" in UTC terms

    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    service.discard(treasure.id)  # allowed: locally it's already Jan 16

    assert meta.get_last_discard_date() == date(2026, 1, 16)


def test_discard_unknown_treasure_raises_not_found():
    service, _, _, _, _ = _build()
    with pytest.raises(NotFound):
        service.discard("nope")
