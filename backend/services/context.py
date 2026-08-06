from dataclasses import dataclass

from aiclients.base import AIClient
from core.constants import TREASURE_POOL_MIN
from core.rng import Rng
from providers.base import ContentProvider
from repos.factory import RepoBundle
from services.economy_service import EconomyService
from services.merger_service import MergerService
from services.rarity_service import RarityService
from services.reward_service import RewardService
from services.stats_service import StatsService
from services.task_service import TaskService
from services.treasure_service import TreasureService


@dataclass
class GameContext:
    """One player's world: repositories, AI, randomness, and content.

    The owner gets a single long-lived context backed by the real database and
    Groq. Each trial visitor gets a throwaway in-memory context with a random
    AI. Services are cheap to build, so they are constructed per call rather
    than cached — the context holds the state, the services hold none.
    """

    repos: RepoBundle
    ai: AIClient
    rng: Rng
    content: ContentProvider
    timezone_name: str = "UTC"
    is_trial: bool = False

    def task_service(self) -> TaskService:
        return TaskService(
            tasks=self.repos.tasks, collectables=self.repos.collectables, ai=self.ai
        )

    def stats_service(self) -> StatsService:
        return StatsService(tasks=self.repos.tasks, timezone_name=self.timezone_name)

    def merger_service(self) -> MergerService:
        return MergerService(collectables=self.repos.collectables, rng=self.rng)

    def economy_service(self) -> EconomyService:
        return EconomyService(collectables=self.repos.collectables, wallet=self.repos.wallet)

    def rarity_service(self) -> RarityService:
        return RarityService(receptacles=self.repos.receptacles)

    def reward_service(self) -> RewardService:
        return RewardService(
            receptacles=self.repos.receptacles,
            collectables=self.repos.collectables,
            wallet=self.repos.wallet,
            rarity=self.rarity_service(),
            ai=self.ai,
            rng=self.rng,
        )

    def treasure_service(self) -> TreasureService:
        return TreasureService(
            treasures=self.repos.treasures,
            receptacles=self.repos.receptacles,
            wallet=self.repos.wallet,
            meta=self.repos.meta,
            rarity=self.rarity_service(),
            content=self.content,
            rng=self.rng,
            timezone_name=self.timezone_name,
            # Trial sandboxes seed a small, curated set of demo rewards and
            # should show the full loop immediately, not wait for a
            # real-economy-sized backlog (services/trial.py:STARTER_REWARDS).
            pool_min=0 if self.is_trial else TREASURE_POOL_MIN,
        )
