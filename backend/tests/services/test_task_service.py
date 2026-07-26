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
    """avg=50%, each virtue=50%, Value=10 -> ~2-3 fragments per base element (ARCHITECTURE §7.1)."""
    service, _, collectables_repo = _make_service(
        [_ai_response(10, awareness=50, curiosity=50, willpower=50, compassion=50, discipline=50)]
    )
    task = service.complete_task("went for a run")

    assert task.value == 10
    for element in BASE_ELEMENTS:
        assert task.fragments_awarded[element] in (2, 3)

    stock = collectables_repo.get_all()
    for element in BASE_ELEMENTS:
        assert stock[(element, CollectableRarity.FRAGMENT)] == task.fragments_awarded[element]


def test_rounds_to_zero_and_omits_element_and_skips_collectable_adjust():
    service, _, collectables_repo = _make_service(
        [_ai_response(1, awareness=5, curiosity=5, willpower=5, compassion=5, discipline=5)]
    )
    task = service.complete_task("blinked")

    assert task.fragments_awarded == {}
    stock = collectables_repo.get_all()
    assert all(count == 0 for count in stock.values())


def test_only_the_relevant_element_gets_fragments_when_one_virtue_dominates():
    # avg = mean(0,0,100,0,0) = 20; Willpower maps to Fire.
    service, _, _ = _make_service(
        [_ai_response(100, awareness=0, curiosity=0, willpower=100, compassion=0, discipline=0)]
    )
    task = service.complete_task("intense workout")

    expected_fire = round((20 / 100) * (100 / 100) * 100)
    assert task.fragments_awarded[Element.FIRE] == expected_fire
    assert Element.SPACE not in task.fragments_awarded  # Awareness 0 -> rounds to 0


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
