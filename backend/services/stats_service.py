from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core.entities import Task
from core.enums import TaskVirtue
from repos.interfaces import TaskRepository

STATS_WINDOW_DAYS = 30
# How far back to look for streak purposes — generously beyond the display
# window so a long unbroken streak isn't silently truncated.
STREAK_LOOKBACK_DAYS = 400


@dataclass
class Stats:
    per_day: dict[str, int]
    virtue_means: dict[TaskVirtue, float]
    streak: int


class StatsService:
    def __init__(
        self,
        tasks: TaskRepository,
        timezone_name: str = "UTC",
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._tasks = tasks
        self._tz = ZoneInfo(timezone_name)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def get_stats(self) -> Stats:
        now_local = self._now().astimezone(self._tz)
        today = now_local.date()

        lookback_since = (now_local - timedelta(days=STREAK_LOOKBACK_DAYS)).astimezone(
            timezone.utc
        )
        tasks = self._tasks.list_since(lookback_since)

        window_start = today - timedelta(days=STATS_WINDOW_DAYS - 1)
        per_day: dict[str, int] = defaultdict(int)
        virtue_totals: dict[TaskVirtue, int] = defaultdict(int)
        virtue_counts: dict[TaskVirtue, int] = defaultdict(int)

        for task in tasks:
            local_date = task.created_at.astimezone(self._tz).date()
            if local_date >= window_start:
                per_day[local_date.isoformat()] += 1
                for virtue, value in task.virtues.items():
                    virtue_totals[virtue] += value
                    virtue_counts[virtue] += 1

        virtue_means = {
            virtue: (
                virtue_totals[virtue] / virtue_counts[virtue] if virtue_counts[virtue] else 0.0
            )
            for virtue in TaskVirtue
        }

        return Stats(
            per_day=dict(per_day),
            virtue_means=virtue_means,
            streak=self._current_streak(tasks, today),
        )

    def _current_streak(self, tasks: list[Task], today: date) -> int:
        days_with_tasks = {task.created_at.astimezone(self._tz).date() for task in tasks}
        streak = 0
        day = today
        while day in days_with_tasks:
            streak += 1
            day -= timedelta(days=1)
        return streak
