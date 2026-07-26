from functools import lru_cache

from django.conf import settings

from aiclients.base import AIClient
from aiclients.groq_client import GroqClient
from aiclients.random_client import RandomAIClient
from core.rng import Rng, SystemRng
from repos.factory import RepoBundle, build_repos
from services.economy_service import EconomyService
from services.merger_service import MergerService
from services.rarity_service import RarityService
from services.reward_service import RewardService
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


@lru_cache(maxsize=1)
def get_rng() -> Rng:
    return SystemRng()


def get_task_service() -> TaskService:
    repos = get_repos()
    return TaskService(tasks=repos.tasks, collectables=repos.collectables, ai=get_ai_client())


def get_stats_service() -> StatsService:
    return StatsService(tasks=get_repos().tasks, timezone_name=settings.TIME_ZONE)


def get_merger_service() -> MergerService:
    return MergerService(collectables=get_repos().collectables, rng=get_rng())


def get_economy_service() -> EconomyService:
    repos = get_repos()
    return EconomyService(collectables=repos.collectables, wallet=repos.wallet)


def get_rarity_service() -> RarityService:
    return RarityService(receptacles=get_repos().receptacles)


def get_reward_service() -> RewardService:
    return RewardService(
        receptacles=get_repos().receptacles,
        rarity=get_rarity_service(),
        ai=get_ai_client(),
        rng=get_rng(),
    )
