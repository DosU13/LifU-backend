from datetime import datetime, timedelta, timezone

import pytest

from aiclients.fake import FakeAIClient
from core.entities import Task
from core.enums import CollectableRarity, Element, TaskVirtue
from core.errors import AIResponseInvalid
from repos.memory import MemoryCollectableRepository, MemoryTaskRepository
from services.task_service import TaskService

BASE_ELEMENTS = (Element.SPACE, Element.AIR, Element.FIRE, Element.WATER, Element.EARTH)


def _ai_response(value, awareness=0, curiosity=0, willpower=0, compassion=0, discipline=0) -> dict:
    return {
        "Value": value,
        "Awareness": awareness,
        "Curiosity": curiosity,
        "Willpower": willpower,
        "Compassion": compassion,
        "Discipline": discipline,
    }


def _make_service(responses):
    tasks_repo = MemoryTaskRepository()
    collectables_repo = MemoryCollectableRepository()
    ai = FakeAIClient(responses)
    service = TaskService(tasks=tasks_repo, collectables=collectables_repo, ai=ai)
    return service, tasks_repo, collectables_repo


def test_value10_50pct_example_from_architecture():
    """All virtues equal -> value splits evenly, 2 per element, summing to value (§7.1)."""
    service, _, collectables_repo = _make_service(
        [_ai_response(10, awareness=50, curiosity=50, willpower=50, compassion=50, discipline=50)]
    )
    task = service.complete_task("went for a run")

    assert task.value == 10
    for element in BASE_ELEMENTS:
        assert task.fragments_awarded[element] == 2
    assert sum(task.fragments_awarded.values()) == 10

    stock = collectables_repo.get_all()
    for element in BASE_ELEMENTS:
        assert stock[(element, CollectableRarity.FRAGMENT)] == task.fragments_awarded[element]


def test_sum_of_fragments_tracks_value_regardless_of_how_many_virtues_score_high():
    """The bug this formula replaced: sum(fragments) scaled with value * avg^2, not value,
    so a task scoring high on several virtues could total far more than its own value while
    a narrowly-focused task totaled far less. Proportionality must hold either way now."""
    service, _, _ = _make_service(
        [_ai_response(50, awareness=90, curiosity=80, willpower=70, compassion=60, discipline=85)]
    )
    task = service.complete_task("finished a big multi-part project")

    assert sum(task.fragments_awarded.values()) == 50


def test_all_virtues_zero_awards_nothing_without_dividing_by_zero():
    # The AI returns all-zero for empty/nonsense text (ARCHITECTURE §8) -- total_virtue
    # would be 0, so the share formula must special-case this rather than divide by it.
    service, _, collectables_repo = _make_service([_ai_response(0)])
    task = service.complete_task("")

    assert task.fragments_awarded == {}
    assert all(count == 0 for count in collectables_repo.get_all().values())


def test_rounds_to_zero_and_omits_element_and_skips_collectable_adjust():
    service, _, collectables_repo = _make_service(
        [_ai_response(1, awareness=5, curiosity=5, willpower=5, compassion=5, discipline=5)]
    )
    task = service.complete_task("blinked")

    assert task.fragments_awarded == {}
    stock = collectables_repo.get_all()
    assert all(count == 0 for count in stock.values())


def test_only_the_relevant_element_gets_fragments_when_one_virtue_dominates():
    # Willpower maps to Fire; it's the only nonzero virtue, so it takes 100% of value.
    service, _, _ = _make_service(
        [_ai_response(100, awareness=0, curiosity=0, willpower=100, compassion=0, discipline=0)]
    )
    task = service.complete_task("intense workout")

    assert task.fragments_awarded == {Element.FIRE: 100}
    assert Element.SPACE not in task.fragments_awarded  # Awareness 0 -> no share at all


def test_persists_task_with_correct_fields():
    service, tasks_repo, _ = _make_service([_ai_response(10, discipline=100)])
    task = service.complete_task("did chores")

    stored = tasks_repo.list_since(datetime(2000, 1, 1, tzinfo=timezone.utc))
    assert len(stored) == 1
    assert stored[0].id == task.id
    assert stored[0].text == "did chores"
    assert stored[0].virtues[TaskVirtue.DISCIPLINE] == 100
    assert stored[0].created_at.tzinfo is not None


def test_propagates_ai_response_invalid_after_retries_exhausted():
    service, tasks_repo, collectables_repo = _make_service([{"bad": 1}, {"bad": 1}, {"bad": 1}])
    with pytest.raises(AIResponseInvalid):
        service.complete_task("text")
    # nothing should have been persisted or awarded
    assert tasks_repo.list_since(datetime(2000, 1, 1, tzinfo=timezone.utc)) == []
    assert all(count == 0 for count in collectables_repo.get_all().values())


def test_list_recent_filters_by_days():
    service, tasks_repo, _ = _make_service([])
    now = datetime.now(timezone.utc)
    old_task = tasks_repo.add(
        Task(
            id="",
            text="old",
            created_at=now - timedelta(days=10),
            value=1,
            virtues=dict.fromkeys(TaskVirtue, 10),
            fragments_awarded={},
        )
    )
    recent_task = tasks_repo.add(
        Task(
            id="",
            text="recent",
            created_at=now - timedelta(hours=1),
            value=1,
            virtues=dict.fromkeys(TaskVirtue, 10),
            fragments_awarded={},
        )
    )

    assert {t.id for t in service.list_recent(days=5)} == {recent_task.id}
    assert {t.id for t in service.list_recent(days=30)} == {old_task.id, recent_task.id}
