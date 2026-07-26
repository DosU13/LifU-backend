"""Repository contract tests — behavior every backend implementation must satisfy.

These are mixins, not runnable on their own (the `repo` fixture raises
NotImplementedError). Concrete test modules subclass them and override `repo`
to bind a real backend — see tests/repos/test_memory.py for the memory
backend. Phase 4 reuses these same classes for a Firebase-backed subclass,
run only when FIREBASE_CREDENTIALS is set.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from core.entities import Receptacle, Task, Treasure
from core.enums import (
    CollectableRarity,
    Element,
    ReceptacleRarity,
    ReceptacleState,
    TaskVirtue,
    Virtue,
)
from core.errors import AlreadyExists, InsufficientCoins, InsufficientCollectables, NotFound

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TaskRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def test_add_assigns_id_and_is_retrievable(self, repo):
        task = Task(
            id="",
            text="ran 5k",
            created_at=NOW,
            value=10,
            virtues={TaskVirtue.WILLPOWER: 60},
            fragments_awarded={Element.FIRE: 2},
        )
        stored = repo.add(task)
        assert stored.id
        assert stored.text == "ran 5k"

    def test_list_since_filters_and_orders_by_created_at(self, repo):
        def task(text, when):
            return Task(
                id="", text=text, created_at=when, value=1, virtues={}, fragments_awarded={}
            )

        repo.add(task("old", NOW - timedelta(days=5)))
        repo.add(task("recent", NOW))
        repo.add(task("mid", NOW - timedelta(days=1)))

        results = repo.list_since(NOW - timedelta(days=2))
        assert [t.text for t in results] == ["mid", "recent"]

    def test_returned_task_is_isolated_from_internal_state(self, repo):
        task = Task(
            id="",
            text="x",
            created_at=NOW,
            value=1,
            virtues={TaskVirtue.WILLPOWER: 10},
            fragments_awarded={Element.FIRE: 1},
        )
        stored = repo.add(task)
        stored.virtues[TaskVirtue.WILLPOWER] = 999
        refetched = repo.list_since(NOW - timedelta(days=1))[0]
        assert refetched.virtues[TaskVirtue.WILLPOWER] == 10


class CollectableRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def test_get_all_starts_at_96_zeroed_entries(self, repo):
        stock = repo.get_all()
        assert len(stock) == 96
        assert all(v == 0 for v in stock.values())

    def test_adjust_applies_positive_and_negative_deltas(self, repo):
        repo.adjust({(Element.FIRE, CollectableRarity.FRAGMENT): 5})
        repo.adjust({(Element.FIRE, CollectableRarity.FRAGMENT): -2})
        assert repo.get_all()[(Element.FIRE, CollectableRarity.FRAGMENT)] == 3

    def test_adjust_is_atomic_all_or_nothing(self, repo):
        repo.adjust({(Element.FIRE, CollectableRarity.FRAGMENT): 3})
        with pytest.raises(InsufficientCollectables):
            repo.adjust(
                {
                    (Element.FIRE, CollectableRarity.FRAGMENT): -1,  # fine alone
                    (Element.WATER, CollectableRarity.FRAGMENT): -1,  # fails: 0 stock
                }
            )
        # the Fire delta must NOT have applied despite being individually valid
        assert repo.get_all()[(Element.FIRE, CollectableRarity.FRAGMENT)] == 3
        assert repo.get_all()[(Element.WATER, CollectableRarity.FRAGMENT)] == 0

    def test_adjust_rejects_negative_result_for_untouched_zero_stock(self, repo):
        with pytest.raises(InsufficientCollectables):
            repo.adjust({(Element.AIR, CollectableRarity.CORE): -1})


class WalletRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def test_starts_at_zero(self, repo):
        assert repo.get_coins() == 0

    def test_adjust_credits_and_debits(self, repo):
        assert repo.adjust(100) == 100
        assert repo.adjust(-30) == 70
        assert repo.get_coins() == 70

    def test_adjust_floors_at_zero_and_raises(self, repo):
        repo.adjust(10)
        with pytest.raises(InsufficientCoins):
            repo.adjust(-11)
        assert repo.get_coins() == 10  # rejected adjustment left balance unchanged

    def test_adjust_to_exactly_zero_is_allowed(self, repo):
        repo.adjust(5)
        assert repo.adjust(-5) == 0


class ReceptacleRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def _make(self, **overrides):
        base = dict(
            id="",
            state=ReceptacleState.IN_POOL,
            virtue=Virtue.SERENITY,
            rarity=ReceptacleRarity.SAFE,
            value=42,
            is_generated=False,
            is_secret=False,
            friend_name=None,
            reward_text="a nice dinner",
            content=None,
            treasure_id=None,
            created_at=NOW,
        )
        base.update(overrides)
        return Receptacle(**base)

    def test_add_assigns_id(self, repo):
        stored = repo.add(self._make())
        assert stored.id

    def test_get_raises_not_found_for_unknown_id(self, repo):
        with pytest.raises(NotFound):
            repo.get("does-not-exist")

    def test_get_returns_stored_receptacle(self, repo):
        stored = repo.add(self._make())
        fetched = repo.get(stored.id)
        assert fetched.id == stored.id
        assert fetched.reward_text == "a nice dinner"

    def test_update_persists_changes(self, repo):
        stored = repo.add(self._make())
        stored.state = ReceptacleState.DROPPED
        repo.update(stored)
        assert repo.get(stored.id).state == ReceptacleState.DROPPED

    def test_update_unknown_id_raises_not_found(self, repo):
        ghost = self._make(id="ghost")
        with pytest.raises(NotFound):
            repo.update(ghost)

    def test_list_by_state_filters_correctly(self, repo):
        pool = repo.add(self._make())
        dropped = repo.add(self._make(state=ReceptacleState.DROPPED))
        assert [r.id for r in repo.list_by_state(ReceptacleState.IN_POOL)] == [pool.id]
        assert [r.id for r in repo.list_by_state(ReceptacleState.DROPPED)] == [dropped.id]

    def test_list_non_generated_excludes_generated_regardless_of_state(self, repo):
        own = repo.add(self._make())
        generated = repo.add(
            self._make(is_generated=True, reward_text=None, state=ReceptacleState.DROPPED)
        )
        ids = {r.id for r in repo.list_non_generated()}
        assert own.id in ids
        assert generated.id not in ids


class TreasureRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def _make(self, **overrides):
        base = dict(
            id="t0",
            slot=0,
            receptacle_ids=["r1", "r2"],
            pity={ReceptacleRarity.VAULT: 0, ReceptacleRarity.SANCTUM: 0},
            created_at=NOW,
        )
        base.update(overrides)
        return Treasure(**base)

    def test_save_and_get_all(self, repo):
        repo.save(self._make())
        all_treasures = repo.get_all()
        assert len(all_treasures) == 1
        assert all_treasures[0].id == "t0"

    def test_save_upserts_existing_id(self, repo):
        repo.save(self._make())
        repo.save(self._make(receptacle_ids=["r3"]))
        all_treasures = repo.get_all()
        assert len(all_treasures) == 1
        assert all_treasures[0].receptacle_ids == ["r3"]

    def test_delete_removes_treasure(self, repo):
        repo.save(self._make())
        repo.delete("t0")
        assert repo.get_all() == []

    def test_delete_unknown_id_is_a_noop(self, repo):
        repo.delete("does-not-exist")  # must not raise


class FriendLinkRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def test_add_creates_link_with_timestamp(self, repo):
        link = repo.add("alex")
        assert link.name == "alex"
        assert link.created_at is not None

    def test_add_duplicate_raises_already_exists(self, repo):
        repo.add("alex")
        with pytest.raises(AlreadyExists):
            repo.add("alex")

    def test_get_returns_none_for_unknown(self, repo):
        assert repo.get("nobody") is None

    def test_get_returns_existing_link(self, repo):
        repo.add("sam")
        assert repo.get("sam").name == "sam"

    def test_list_all_returns_every_link(self, repo):
        repo.add("a")
        repo.add("b")
        assert {link.name for link in repo.list_all()} == {"a", "b"}


class MetaRepositoryContract:
    @pytest.fixture
    def repo(self):
        raise NotImplementedError

    def test_starts_with_no_discard_date(self, repo):
        assert repo.get_last_discard_date() is None

    def test_set_and_get_round_trip(self, repo):
        d = date(2026, 1, 15)
        repo.set_last_discard_date(d)
        assert repo.get_last_discard_date() == d

    def test_set_overwrites_previous_value(self, repo):
        repo.set_last_discard_date(date(2026, 1, 15))
        repo.set_last_discard_date(date(2026, 1, 16))
        assert repo.get_last_discard_date() == date(2026, 1, 16)
