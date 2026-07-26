import pytest

from aiclients.fake import FakeAIClient
from core.enums import ReceptacleRarity, ReceptacleState, Virtue
from core.errors import AIResponseInvalid
from core.rng import SeededRng
from repos.memory import MemoryReceptacleRepository
from services.rarity_service import RarityService
from services.reward_service import RewardService


def _make_service(responses, rng=None):
    repo = MemoryReceptacleRepository()
    service = RewardService(
        receptacles=repo,
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


def test_list_by_state_filters():
    service, repo = _make_service([{"Value": 10, "Class": ["Serenity"]}])
    created = service.submit_reward("reward")

    assert [r.id for r in service.list_by_state(ReceptacleState.IN_POOL)] == [created.id]
    assert service.list_by_state(ReceptacleState.OPENED) == []
