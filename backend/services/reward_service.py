from collections.abc import Callable
from datetime import datetime, timezone

from aiclients.base import AIClient
from aiclients.validation import get_reward_classification
from core.entities import Receptacle
from core.enums import ReceptacleRarity, ReceptacleState
from core.errors import DomainError, InsufficientCollectables, MissingKey
from core.mappings import key_for_receptacle
from core.rng import Rng
from repos.interfaces import CollectableRepository, ReceptacleRepository, WalletRepository
from services.rarity_service import RarityService


class RewardService:
    def __init__(
        self,
        receptacles: ReceptacleRepository,
        collectables: CollectableRepository,
        wallet: WalletRepository,
        rarity: RarityService,
        ai: AIClient,
        rng: Rng,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._receptacles = receptacles
        self._collectables = collectables
        self._wallet = wallet
        self._rarity = rarity
        self._ai = ai
        self._rng = rng
        self._now = now or (lambda: datetime.now(timezone.utc))

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

    def open_receptacle(self, receptacle_id: str) -> tuple[Receptacle, int, int]:
        """Spend the matching collectable to open a dropped receptacle.

        The key is the receptacle's virtue as a combined element at the
        matching rarity index — a Safe of Serenity needs one Ocean Essence
        (ARCHITECTURE §7.5). Returns (receptacle, coins_gained, coins).
        """
        receptacle = self._receptacles.get(receptacle_id)
        if receptacle.state is not ReceptacleState.DROPPED:
            raise DomainError(
                f"receptacle {receptacle_id} is {receptacle.state.value}, not DROPPED"
            )

        key = key_for_receptacle(receptacle.virtue, receptacle.rarity)
        try:
            self._collectables.adjust({key: -1})
        except InsufficientCollectables as exc:
            raise MissingKey(*key) from exc

        coins_gained = receptacle.value
        coins = self._wallet.adjust(coins_gained)

        receptacle.state = ReceptacleState.OPENED
        receptacle.opened_at = self._now()
        self._receptacles.update(receptacle)

        self._rarity.recalculate()
        return self._receptacles.get(receptacle_id), coins_gained, coins

    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]:
        return self._receptacles.list_by_state(state)
