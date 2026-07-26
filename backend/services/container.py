from functools import lru_cache

from django.conf import settings

from aiclients.base import AIClient
from aiclients.groq_client import GroqClient
from aiclients.random_client import RandomAIClient
from repos.factory import RepoBundle, build_repos
from services.stats_service import StatsService
from services.task_service import TaskService


@lru_cache(maxsize=1)
def get_repos() -> RepoBundle:
    """Process-wide repository bundle.

    Memory-only for now — real/trial backend selection per request context
    lands in Phase 11 (auth/trial).
    """
    return build_repos("memory")


@lru_cache(maxsize=1)
def get_ai_client() -> AIClient:
    if settings.GROQ_API_KEY:
        return GroqClient(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    return RandomAIClient()


def get_task_service() -> TaskService:
    repos = get_repos()
    return TaskService(tasks=repos.tasks, collectables=repos.collectables, ai=get_ai_client())


def get_stats_service() -> StatsService:
    return StatsService(tasks=get_repos().tasks, timezone_name=settings.TIME_ZONE)
