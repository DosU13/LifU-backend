from datetime import datetime, timedelta, timezone

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
        fragments[e] = round((virtue_for_e / total_virtue) * value * VIRTUE_TUNER)
        `value` is split across elements by each virtue's *share* of the task's
        own virtue total, rather than by each virtue's raw percentage scaled by
        the average of all five. The raw-percentage version double-counted the
        average (it appears explicitly, and again inside every virtue_for_e/100
        term, since those are drawn from the same distribution), which made
        sum(fragments) scale with value * avg_virtue^2 instead of value alone —
        a task scored high across several virtues could total 2x its value in
        fragments while a narrowly-focused task totaled well under 1x. This way
        sum(fragments) ≈ value * VIRTUE_TUNER regardless of how many virtues
        the AI rated highly, while a task still puts most of its fragments into
        whichever element its dominant virtue maps to.

        Elements that round to 0 are omitted from both the collectable adjustment
        and the persisted `fragments_awarded`. A task the AI scored as needing
        no virtues at all (total_virtue == 0) awards nothing.
        """
        valuation = get_task_valuation(self._ai, text)
        total_virtue = sum(valuation.virtues.values())

        fragments: dict[Element, int] = {}
        if total_virtue:
            for element, task_virtue in ELEMENT_TASK_VIRTUE.items():
                amount = round(
                    (valuation.virtues[task_virtue] / total_virtue) * valuation.value * VIRTUE_TUNER
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
