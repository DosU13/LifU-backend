from datetime import datetime, timezone

import pytest

from aiclients.fake import FakeAIClient
from core.entities import Receptacle
from core.enums import CollectableRarity, Element, ReceptacleRarity, ReceptacleState, Virtue
from core.errors import AIResponseInvalid, DomainError, MissingKey
from core.rng import SeededRng
from repos.memory import (
    MemoryCollectableRepository,
    MemoryReceptacleRepository,
    MemoryWalletRepository,
)
from services.rarity_service import RarityService
from services.reward_service import RewardService


def _make_service(responses, rng=None):
    repo = MemoryReceptacleRepository()
    collectables = MemoryCollectableRepository()
    wallet = MemoryWalletRepository()
    service = RewardService(
        receptacles=repo,
        collectables=collectables,
        wallet=wallet,
        rarity=RarityService(repo),
        ai=FakeAIClient(responses),
        rng=rng or SeededRng(1),
    )
    return service, repo


def test_submit_reward_creates_pool_receptacle():
    service, repo = _make_service([{"Value": 42, "Class": ["Serenity"]}])

    receptacle = service.submit_reward("a quiet evening")

    assert receptacle.id
    assert receptacle.state is ReceptacleState.IN_POOL
    assert receptacle.virtue is Virtue.SERENITY
    assert receptacle.value == 42
    assert receptacle.reward_text == "a quiet evening"
    assert receptacle.is_generated is False
    assert receptacle.is_secret is False
    assert repo.get(receptacle.id).id == receptacle.id


def test_submit_reward_picks_virtue_from_returned_classes():
    classes = ["Serenity", "Freedom", "Vitality"]
    service, _ = _make_service([{"Value": 10, "Class": classes}])

    receptacle = service.submit_reward("something nice")

    assert receptacle.virtue.name.title() in classes


def test_submit_reward_triggers_rarity_recalculation():
    """Rarity comes from the ratio recalculation, not the placeholder written at creation."""
    service, repo = _make_service(
        [{"Value": 90, "Class": ["Serenity"]}, {"Value": 10, "Class": ["Freedom"]}]
    )

    high = service.submit_reward("great reward")
    low = service.submit_reward("small reward")

    # apportion(2) -> 1 Safe + 1 Chest; the higher-value reward takes the rarer slot
    assert repo.get(high.id).rarity is ReceptacleRarity.SAFE
    assert repo.get(low.id).rarity is ReceptacleRarity.CHEST


def test_submit_secret_reward_records_flag_and_friend():
    service, _ = _make_service([{"Value": 85, "Class": ["Nurturing"]}])

    receptacle = service.submit_reward(
        "I promise you lunch", is_secret=True, friend_name="alex"
    )

    assert receptacle.is_secret is True
    assert receptacle.friend_name == "alex"
    # the text is still stored — the API layer is what withholds it
    assert receptacle.reward_text == "I promise you lunch"


def test_submit_secret_reward_value_floored_to_51():
    service, _ = _make_service([{"Value": 5, "Class": ["Inspiration"]}])

    receptacle = service.submit_reward("just a note", is_secret=True)

    assert receptacle.value == 51


def test_submit_reward_ai_failure_persists_nothing():
    service, repo = _make_service([{"bad": 1}, {"bad": 1}, {"bad": 1}])

    with pytest.raises(AIResponseInvalid):
        service.submit_reward("text")

    assert repo.list_non_generated() == []


def _drop(repo, receptacle_id):
    receptacle = repo.get(receptacle_id)
    receptacle.state = ReceptacleState.DROPPED
    repo.update(receptacle)
    return receptacle


def test_open_consumes_the_matching_key_and_pays_coins():
    """A Safe of Serenity opens with exactly one Ocean Essence."""
    repo = MemoryReceptacleRepository()
    collectables = MemoryCollectableRepository()
    wallet = MemoryWalletRepository()
    service = RewardService(
        receptacles=repo,
        collectables=collectables,
        wallet=wallet,
        rarity=RarityService(repo),
        ai=FakeAIClient(
            [{"Value": 60, "Class": ["Serenity"]}, {"Value": 10, "Class": ["Freedom"]}]
        ),
        rng=SeededRng(1),
    )
    created = service.submit_reward("nice dinner")
    service.submit_reward("filler")  # apportion(2) -> the first is the Safe
    assert repo.get(created.id).rarity is ReceptacleRarity.SAFE
    _drop(repo, created.id)
    collectables.adjust({(Element.OCEAN, CollectableRarity.ESSENCE): 1})

    opened, coins_gained, coins = service.open_receptacle(created.id)

    assert opened.state is ReceptacleState.OPENED
    assert opened.opened_at is not None
    assert coins_gained == 60
    assert coins == 60
    assert wallet.get_coins() == 60
    assert collectables.get_all()[(Element.OCEAN, CollectableRarity.ESSENCE)] == 0


def test_open_without_the_key_raises_missing_key_and_changes_nothing():
    repo = MemoryReceptacleRepository()
    collectables = MemoryCollectableRepository()
    wallet = MemoryWalletRepository()
    service = RewardService(
        receptacles=repo,
        collectables=collectables,
        wallet=wallet,
        rarity=RarityService(repo),
        ai=FakeAIClient([{"Value": 30, "Class": ["Serenity"]}]),
        rng=SeededRng(1),
    )
    created = service.submit_reward("reward")
    _drop(repo, created.id)

    with pytest.raises(MissingKey) as excinfo:
        service.open_receptacle(created.id)

    assert excinfo.value.element is Element.OCEAN
    assert excinfo.value.rarity is CollectableRarity.CRYSTAL  # lone receptacle -> Chest
    assert repo.get(created.id).state is ReceptacleState.DROPPED
    assert wallet.get_coins() == 0


def test_open_rejects_receptacle_that_is_not_dropped():
    repo = MemoryReceptacleRepository()
    collectables = MemoryCollectableRepository()
    service = RewardService(
        receptacles=repo,
        collectables=collectables,
        wallet=MemoryWalletRepository(),
        rarity=RarityService(repo),
        ai=FakeAIClient([{"Value": 30, "Class": ["Serenity"]}]),
        rng=SeededRng(1),
    )
    created = service.submit_reward("reward")  # still IN_POOL
    collectables.adjust({(Element.OCEAN, CollectableRarity.CRYSTAL): 1})

    with pytest.raises(DomainError):
        service.open_receptacle(created.id)

    # the key must not have been spent
    assert collectables.get_all()[(Element.OCEAN, CollectableRarity.CRYSTAL)] == 1


def test_opened_receptacle_keeps_its_rarity_frozen_afterwards():
    repo = MemoryReceptacleRepository()
    collectables = MemoryCollectableRepository()
    service = RewardService(
        receptacles=repo,
        collectables=collectables,
        wallet=MemoryWalletRepository(),
        rarity=RarityService(repo),
        ai=FakeAIClient([{"Value": 5, "Class": ["Serenity"]}]),
        rng=SeededRng(1),
    )
    created = service.submit_reward("small reward")
    _drop(repo, created.id)
    collectables.adjust({(Element.OCEAN, CollectableRarity.CRYSTAL): 1})
    service.open_receptacle(created.id)

    # add many higher-value receptacles; the opened one must keep its Chest rarity
    rarity_service = RarityService(repo)
    for value in range(100, 60, -1):
        repo.add(
            Receptacle(
                id="",
                state=ReceptacleState.IN_POOL,
                virtue=Virtue.SERENITY,
                rarity=ReceptacleRarity.CHEST,
                value=value,
                is_generated=False,
                is_secret=False,
                friend_name=None,
                reward_text="x",
                content=None,
                treasure_id=None,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
    rarity_service.recalculate()

    assert repo.get(created.id).rarity is ReceptacleRarity.CHEST


def test_list_by_state_filters():
    service, repo = _make_service([{"Value": 10, "Class": ["Serenity"]}])
    created = service.submit_reward("reward")

    assert [r.id for r in service.list_by_state(ReceptacleState.IN_POOL)] == [created.id]
    assert service.list_by_state(ReceptacleState.OPENED) == []
