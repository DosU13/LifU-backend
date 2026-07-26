from datetime import datetime, timedelta, timezone
from statistics import mean

from aiclients.base import AIClient
from aiclients.validation import get_task_valuation
from core.constants import VIRTUE_TUNER
from core.entities import Task
from core.enums import CollectableRarity, Element
from core.mappings import ELEMENT_TASK_VIRTUE
from repos.interfaces import CollectableRepository, TaskRepository


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        collectables: CollectableRepository,
        ai: AIClient,
    ) -> None:
        self._tasks = tasks
        self._collectables = collectables
        self._ai = ai

    def complete_task(self, text: str) -> Task:
        """Value the task via AI, award base-element fragments, persist, and return it.

        Fragment formula (ARCHITECTURE §7.1):
        fragments[e] = round((avg_virtue/100) * (virtue_for_e/100) * value * VIRTUE_TUNER)
        Elements that round to 0 are omitted from both the collectable adjustment
        and the persisted `fragments_awarded`.
        """
        valuation = get_task_valuation(self._ai, text)
        avg_virtue = mean(valuation.virtues.values())

        fragments: dict[Element, int] = {}
        for element, task_virtue in ELEMENT_TASK_VIRTUE.items():
            amount = round(
                (avg_virtue / 100)
                * (valuation.virtues[task_virtue] / 100)
                * valuation.value
                * VIRTUE_TUNER
            )
            if amount:
                fragments[element] = amount

        if fragments:
            self._collectables.adjust(
                {(element, CollectableRarity.FRAGMENT): n for element, n in fragments.items()}
            )

        return self._tasks.add(
            Task(
                id="",
                text=text,
                created_at=datetime.now(timezone.utc),
                value=valuation.value,
                virtues=dict(valuation.virtues),
                fragments_awarded=fragments,
            )
        )

    def list_recent(self, days: int = 30) -> list[Task]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return self._tasks.list_since(since)
