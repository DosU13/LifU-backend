from datetime import datetime, timedelta, timezone

import pytest

from core.entities import Receptacle
from core.enums import ReceptacleRarity, ReceptacleState, Virtue
from repos.memory import MemoryReceptacleRepository
from services.rarity_service import RarityService, apportion

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

C = ReceptacleRarity.CHEST
S = ReceptacleRarity.SAFE
V = ReceptacleRarity.VAULT
SANCTUM = ReceptacleRarity.SANCTUM


def _receptacle(
    value: int,
    *,
    created_at: datetime | None = None,
    state: ReceptacleState = ReceptacleState.IN_POOL,
    is_generated: bool = False,
    rarity: ReceptacleRarity = ReceptacleRarity.CHEST,
) -> Receptacle:
    return Receptacle(
        id="",
        state=state,
        virtue=Virtue.SERENITY,
        rarity=rarity,
        value=value,
        is_generated=is_generated,
        is_secret=False,
        friend_name=None,
        reward_text="reward",
        content=None,
        treasure_id=None,
        created_at=created_at or BASE_TIME,
    )


def _rarity_counts(repo: MemoryReceptacleRepository) -> dict[ReceptacleRarity, int]:
    counts: dict[ReceptacleRarity, int] = {}
    for receptacle in repo.list_non_generated():
        counts[receptacle.rarity] = counts.get(receptacle.rarity, 0) + 1
    return counts


# --- apportion(): the pure math ---


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, {C: 0, S: 0, V: 0, SANCTUM: 0}),
        (1, {C: 1, S: 0, V: 0, SANCTUM: 0}),
        (4, {C: 3, S: 1, V: 0, SANCTUM: 0}),
        (14, {C: 10, S: 3, V: 1, SANCTUM: 0}),
        (18, {C: 12, S: 4, V: 1, SANCTUM: 1}),  # first N where a Sanctum appears
        (40, {C: 27, S: 9, V: 3, SANCTUM: 1}),  # the exact 27:9:3:1 ratio
        (80, {C: 54, S: 18, V: 6, SANCTUM: 2}),
    ],
)
def test_apportion_matches_documented_examples(n, expected):
    assert apportion(n) == expected


@pytest.mark.parametrize("n", range(0, 200))
def test_apportion_always_allocates_exactly_n_slots(n):
    assert sum(apportion(n).values()) == n


def test_apportion_ties_favor_the_more_common_rarity():
    # n=20 gives every rarity a remainder of exactly 0.5 -> the 2 leftover
    # slots must go to Chest then Safe, never to Vault/Sanctum.
    assert apportion(20) == {C: 14, S: 5, V: 1, SANCTUM: 0}


# --- recalculate(): assignment by rank ---


def test_recalculate_assigns_rarest_slots_to_highest_values():
    repo = MemoryReceptacleRepository()
    for value in range(40, 0, -1):  # 40 receptacles, values 40 down to 1
        repo.add(_receptacle(value))

    RarityService(repo).recalculate()

    by_value = {r.value: r.rarity for r in repo.list_non_generated()}
    assert by_value[40] == SANCTUM  # rank 1
    assert by_value[39] == V  # ranks 2-4
    assert by_value[37] == V
    assert by_value[36] == S  # ranks 5-13
    assert by_value[28] == S
    assert by_value[27] == C  # ranks 14-40
    assert by_value[1] == C
    assert _rarity_counts(repo) == {C: 27, S: 9, V: 3, SANCTUM: 1}


def test_recalculate_tie_break_older_receptacle_wins_rarer_slot():
    repo = MemoryReceptacleRepository()
    older = repo.add(_receptacle(50, created_at=BASE_TIME))
    newer = repo.add(_receptacle(50, created_at=BASE_TIME + timedelta(hours=1)))
    for _ in range(2):  # pad to n=4 -> 3 Chest + 1 Safe
        repo.add(_receptacle(10, created_at=BASE_TIME + timedelta(days=1)))

    RarityService(repo).recalculate()

    assert repo.get(older.id).rarity == S
    assert repo.get(newer.id).rarity == C


def test_recalculate_ignores_generated_receptacles():
    repo = MemoryReceptacleRepository()
    real = repo.add(_receptacle(100))
    generated = repo.add(
        _receptacle(100, is_generated=True, rarity=ReceptacleRarity.POUCH)
    )

    RarityService(repo).recalculate()

    assert repo.get(real.id).rarity == C  # n=1 -> single Chest
    assert repo.get(generated.id).rarity == ReceptacleRarity.POUCH  # untouched


def test_opened_receptacle_keeps_frozen_rarity_but_consumes_its_slot():
    """An opened receptacle at rank 1 eats the Sanctum slot without becoming one."""
    repo = MemoryReceptacleRepository()
    # Rank 1 is opened and frozen as a lowly Chest.
    opened_top = repo.add(
        _receptacle(100, state=ReceptacleState.OPENED, rarity=C)
    )
    others = [repo.add(_receptacle(v)) for v in range(99, 60, -1)]  # brings n to 40

    RarityService(repo).recalculate()

    # It kept its frozen rarity...
    assert repo.get(opened_top.id).rarity == C
    # ...and no one else was promoted into the Sanctum slot it consumed.
    counts = _rarity_counts(repo)
    assert counts.get(SANCTUM, 0) == 0
    # Rank 2 still gets the first Vault slot, exactly as if rank 1 were a Sanctum.
    assert repo.get(others[0].id).rarity == V


def test_recalculate_is_idempotent():
    repo = MemoryReceptacleRepository()
    for value in range(25, 0, -1):
        repo.add(_receptacle(value))
    service = RarityService(repo)

    service.recalculate()
    first_pass = {r.id: r.rarity for r in repo.list_non_generated()}
    service.recalculate()
    second_pass = {r.id: r.rarity for r in repo.list_non_generated()}

    assert first_pass == second_pass


def test_recalculate_on_empty_repository_does_nothing():
    repo = MemoryReceptacleRepository()
    RarityService(repo).recalculate()  # must not raise
    assert repo.list_non_generated() == []


def test_recalculate_demotes_when_better_receptacles_arrive():
    repo = MemoryReceptacleRepository()
    lonely = repo.add(_receptacle(10))
    RarityService(repo).recalculate()
    assert repo.get(lonely.id).rarity == C

    # Add 39 higher-value receptacles; the original should stay Chest at the bottom.
    for value in range(100, 61, -1):
        repo.add(_receptacle(value))
    RarityService(repo).recalculate()

    assert repo.get(lonely.id).rarity == C
    assert _rarity_counts(repo) == {C: 27, S: 9, V: 3, SANCTUM: 1}
