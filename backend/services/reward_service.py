from datetime import datetime, timezone

from aiclients.base import AIClient
from aiclients.validation import get_reward_classification
from core.entities import Receptacle
from core.enums import ReceptacleRarity, ReceptacleState
from core.rng import Rng
from repos.interfaces import ReceptacleRepository
from services.rarity_service import RarityService


class RewardService:
    def __init__(
        self,
        receptacles: ReceptacleRepository,
        rarity: RarityService,
        ai: AIClient,
        rng: Rng,
    ) -> None:
        self._receptacles = receptacles
        self._rarity = rarity
        self._ai = ai
        self._rng = rng

    def submit_reward(
        self, text: str, is_secret: bool = False, friend_name: str | None = None
    ) -> Receptacle:
        """Classify a reward, store it as a pool receptacle, and recalculate rarities.

        The virtue is picked at random from the 1-3 classes the AI returned.
        Rarity is never chosen here — it comes from the ratio-based
        recalculation (ARCHITECTURE §7.4), which runs immediately after.
        """
        classification = get_reward_classification(self._ai, text, is_secret=is_secret)
        virtue = self._rng.choice(classification.classes)

        created = self._receptacles.add(
            Receptacle(
                id="",
                state=ReceptacleState.IN_POOL,
                virtue=virtue,
                rarity=ReceptacleRarity.CHEST,  # placeholder; recalculation assigns the real one
                value=classification.value,
                is_generated=False,
                is_secret=is_secret,
                friend_name=friend_name,
                reward_text=text,
                content=None,
                treasure_id=None,
                created_at=datetime.now(timezone.utc),
            )
        )

        self._rarity.recalculate()
        return self._receptacles.get(created.id)

    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]:
        return self._receptacles.list_by_state(state)
