from datetime import datetime, timedelta, timezone

from core.entities import Task
from core.enums import TaskVirtue
from repos.memory import MemoryTaskRepository
from services.stats_service import StatsService


def _task(text: str, created_at: datetime, virtues: dict[TaskVirtue, int] | None = None) -> Task:
    return Task(
        id="",
        text=text,
        created_at=created_at,
        value=10,
        virtues=virtues or dict.fromkeys(TaskVirtue, 10),
        fragments_awarded={},
    )


def test_empty_stats_when_no_tasks():
    service = StatsService(
        tasks=MemoryTaskRepository(),
        timezone_name="UTC",
        now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    stats = service.get_stats()
    assert stats.per_day == {}
    assert stats.streak == 0
    assert all(v == 0.0 for v in stats.virtue_means.values())


def test_streak_uses_local_calendar_day_not_utc():
    """A UTC-late-evening timestamp in Tokyo (UTC+9) falls on the NEXT local day —

    streak must bucket by local day, not the raw UTC date.
    """
    tasks_repo = MemoryTaskRepository()
    # 2026-01-01 20:00 UTC == 2026-01-02 05:00 JST
    tasks_repo.add(_task("a", datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)))
    # 2026-01-02 20:00 UTC == 2026-01-03 05:00 JST
    tasks_repo.add(_task("b", datetime(2026, 1, 2, 20, 0, tzinfo=timezone.utc)))

    # "now" = 2026-01-03 03:00 UTC == 2026-01-03 12:00 JST
    frozen_now = datetime(2026, 1, 3, 3, 0, tzinfo=timezone.utc)
    service = StatsService(tasks=tasks_repo, timezone_name="Asia/Tokyo", now=lambda: frozen_now)

    stats = service.get_stats()
    # JST calendar days with a task: Jan 2 and Jan 3 — consecutive, ending "today" (JST Jan 3)
    assert stats.streak == 2
    assert stats.per_day == {"2026-01-02": 1, "2026-01-03": 1}


def test_streak_is_zero_when_no_task_today():
    tasks_repo = MemoryTaskRepository()
    frozen_now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    tasks_repo.add(_task("yesterday", frozen_now - timedelta(days=1)))

    service = StatsService(tasks=tasks_repo, timezone_name="UTC", now=lambda: frozen_now)
    assert service.get_stats().streak == 0


def test_streak_can_exceed_the_30_day_stats_window():
    tasks_repo = MemoryTaskRepository()
    frozen_now = datetime(2026, 2, 15, 12, 0, tzinfo=timezone.utc)
    for i in range(35):
        tasks_repo.add(_task(f"t{i}", frozen_now - timedelta(days=i)))

    service = StatsService(tasks=tasks_repo, timezone_name="UTC", now=lambda: frozen_now)
    stats = service.get_stats()

    assert stats.streak == 35
    assert len(stats.per_day) == 30  # only the last 30 calendar days appear in per_day


def test_per_day_and_virtue_means_average_correctly():
    tasks_repo = MemoryTaskRepository()
    frozen_now = datetime(2026, 1, 2, 5, 0, tzinfo=timezone.utc)  # UTC, same day as both tasks
    tasks_repo.add(
        _task("a", datetime(2026, 1, 2, 1, 0, tzinfo=timezone.utc), dict.fromkeys(TaskVirtue, 20))
    )
    tasks_repo.add(
        _task("b", datetime(2026, 1, 2, 2, 0, tzinfo=timezone.utc), dict.fromkeys(TaskVirtue, 60))
    )

    service = StatsService(tasks=tasks_repo, timezone_name="UTC", now=lambda: frozen_now)
    stats = service.get_stats()

    assert stats.per_day == {"2026-01-02": 2}
    assert all(mean_value == 40.0 for mean_value in stats.virtue_means.values())


def test_tasks_older_than_stats_window_are_excluded_from_per_day():
    tasks_repo = MemoryTaskRepository()
    frozen_now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    tasks_repo.add(_task("too_old", frozen_now - timedelta(days=31)))
    tasks_repo.add(_task("in_window", frozen_now - timedelta(days=5)))

    service = StatsService(tasks=tasks_repo, timezone_name="UTC", now=lambda: frozen_now)
    stats = service.get_stats()

    assert stats.per_day == {(frozen_now - timedelta(days=5)).date().isoformat(): 1}
