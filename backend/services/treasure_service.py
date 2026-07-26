import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from core.constants import (
    DROP_CHANCES,
    PITY_THRESHOLDS,
    POUCH_VALUE_RANGE,
    SACK_VALUE_RANGE,
    TREASURE_COUNT,
    TREASURE_SIZE_MAX,
    TREASURE_SIZE_MIN,
)
from core.entities import Receptacle, Treasure
from core.enums import ReceptacleRarity, ReceptacleState, Virtue
from core.errors import DiscardAlreadyUsed, NotFound
from core.rng import Rng
from providers.base import ContentProvider
from repos.interfaces import (
    MetaRepository,
    ReceptacleRepository,
    TreasureRepository,
    WalletRepository,
)
from services.rarity_service import RarityService

# Natural drop roll order: rarest first, so a rarer hit always wins.
_ROLL_ORDER: tuple[ReceptacleRarity, ...] = (
    ReceptacleRarity.SANCTUM,
    ReceptacleRarity.VAULT,
    ReceptacleRarity.SAFE,
    ReceptacleRarity.CHEST,
)
# Pity is checked rarest-first too, so a due Sanctum beats a due Vault.
_PITY_ORDER: tuple[ReceptacleRarity, ...] = (
    ReceptacleRarity.SANCTUM,
    ReceptacleRarity.VAULT,
)
_GENERATED_VALUE_RANGES = {
    ReceptacleRarity.POUCH: POUCH_VALUE_RANGE,
    ReceptacleRarity.SACK: SACK_VALUE_RANGE,
}


@dataclass
class BuyResult:
    receptacle: Receptacle
    dropped_rarity: ReceptacleRarity
    price_paid: int
    coins: int
    pity: dict[ReceptacleRarity, int]
    treasure_gone: bool
    was_pity: bool


class TreasureService:
    def __init__(
        self,
        treasures: TreasureRepository,
        receptacles: ReceptacleRepository,
        wallet: WalletRepository,
        meta: MetaRepository,
        rarity: RarityService,
        content: ContentProvider,
        rng: Rng,
        timezone_name: str = "UTC",
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._treasures = treasures
        self._receptacles = receptacles
        self._wallet = wallet
        self._meta = meta
        self._rarity = rarity
        self._content = content
        self._rng = rng
        self._tz = ZoneInfo(timezone_name)
        self._now = now or (lambda: datetime.now(timezone.utc))

    # --- reading ---

    def get_all(self) -> list[Treasure]:
        """Every treasure slot, refilling any that are missing first."""
        self.refill_empty_slots()
        return sorted(self._treasures.get_all(), key=lambda t: t.slot)

    def contents(self, treasure: Treasure) -> list[Receptacle]:
        return [self._receptacles.get(rid) for rid in treasure.receptacle_ids]

    def price(self, treasure: Treasure) -> int:
        """The treasure's fixed price, set when it was generated (ARCHITECTURE §7.6).

        Deliberately *not* recomputed from current contents: buying must not
        get cheaper as the treasure empties.
        """
        return treasure.price

    @staticmethod
    def _initial_price(receptacles: list[Receptacle]) -> int:
        """Average value of the treasure's starting contents."""
        if not receptacles:
            return 1
        return max(1, math.ceil(sum(r.value for r in receptacles) / len(receptacles)))

    # --- generation ---

    def refill_empty_slots(self) -> None:
        """Fill any slot without a treasure. A slot stays empty if the pool is dry."""
        occupied = {t.slot for t in self._treasures.get_all()}
        for slot in range(TREASURE_COUNT):
            if slot not in occupied:
                self.generate(slot)

    def generate(self, slot: int) -> Treasure | None:
        """Draw 5-10 pool receptacles into a new treasure for `slot`.

        Aims for a spread of rarities: pool receptacles are grouped by rarity,
        each group shuffled, then drawn round-robin across the groups.
        Returns None (leaving the slot empty) when the pool has nothing left.
        """
        pool = self._receptacles.list_by_state(ReceptacleState.IN_POOL)
        if not pool:
            return None

        wanted = self._rng.randint(TREASURE_SIZE_MIN, TREASURE_SIZE_MAX)
        drawn = self._draw_spread(pool, min(wanted, len(pool)))

        treasure = Treasure(
            id=uuid.uuid4().hex,
            slot=slot,
            receptacle_ids=[r.id for r in drawn],
            pity=dict.fromkeys(PITY_THRESHOLDS, 0),
            created_at=self._now(),
            price=self._initial_price(drawn),
        )
        self._treasures.save(treasure)

        for receptacle in drawn:
            receptacle.state = ReceptacleState.IN_TREASURE
            receptacle.treasure_id = treasure.id
            self._receptacles.update(receptacle)

        return treasure

    def _draw_spread(self, pool: list[Receptacle], count: int) -> list[Receptacle]:
        groups: dict[ReceptacleRarity, list[Receptacle]] = {}
        for receptacle in pool:
            groups.setdefault(receptacle.rarity, []).append(receptacle)
        for members in groups.values():
            self._rng.shuffle(members)

        order = list(groups)
        self._rng.shuffle(order)

        drawn: list[Receptacle] = []
        while len(drawn) < count:
            drawn_this_pass = False
            for rarity in order:
                if not groups[rarity]:
                    continue
                drawn.append(groups[rarity].pop())
                drawn_this_pass = True
                if len(drawn) == count:
                    break
            if not drawn_this_pass:  # pool exhausted before reaching `count`
                break
        return drawn

    # --- buying ---

    def buy(self, treasure_id: str) -> BuyResult:
        treasure = self._get_treasure(treasure_id)
        price = self.price(treasure)
        coins = self._wallet.adjust(-price)  # raises InsufficientCoins

        rarity, was_pity = self._decide_drop(treasure)

        if rarity in _GENERATED_VALUE_RANGES:
            dropped = self._create_generated(rarity)
        else:
            dropped = self._take_from_treasure(treasure, rarity)

        for tracked in PITY_THRESHOLDS:
            treasure.pity[tracked] = 0 if rarity is tracked else treasure.pity[tracked] + 1

        treasure_gone = not treasure.receptacle_ids
        if treasure_gone:
            self._treasures.delete(treasure.id)
            self.generate(treasure.slot)
        else:
            self._treasures.save(treasure)

        # Recalculation can re-label the receptacle that just dropped (its rarity
        # stays mutable until opened), so `dropped_rarity` records what was won.
        self._rarity.recalculate()

        return BuyResult(
            receptacle=self._receptacles.get(dropped.id),
            dropped_rarity=rarity,
            price_paid=price,
            coins=coins,
            pity=dict(treasure.pity),
            treasure_gone=treasure_gone,
            was_pity=was_pity,
        )

    def _decide_drop(self, treasure: Treasure) -> tuple[ReceptacleRarity, bool]:
        """Which rarity drops, and whether pity forced it.

        Pity only fires when the treasure actually holds that rarity; an
        unfulfillable counter keeps accumulating and pays out on the first
        buy that can honour it.
        """
        held = {r.rarity for r in self.contents(treasure)}

        for rarity in _PITY_ORDER:
            if treasure.pity[rarity] >= PITY_THRESHOLDS[rarity] and rarity in held:
                return rarity, True

        for rarity in _ROLL_ORDER:
            # Roll every tier in order; a tier the treasure lacks falls through.
            if self._rng.random() < DROP_CHANCES[rarity] and rarity in held:
                return rarity, False

        # Sack/Pouch are generated on demand, so this floor is always available.
        if self._rng.random() < DROP_CHANCES[ReceptacleRarity.SACK]:
            return ReceptacleRarity.SACK, False
        return ReceptacleRarity.POUCH, False

    def _take_from_treasure(self, treasure: Treasure, rarity: ReceptacleRarity) -> Receptacle:
        candidates = [r for r in self.contents(treasure) if r.rarity is rarity]
        chosen = self._rng.choice(candidates)

        treasure.receptacle_ids = [rid for rid in treasure.receptacle_ids if rid != chosen.id]
        chosen.state = ReceptacleState.DROPPED
        chosen.treasure_id = None
        self._receptacles.update(chosen)
        return chosen

    def _create_generated(self, rarity: ReceptacleRarity) -> Receptacle:
        low, high = _GENERATED_VALUE_RANGES[rarity]
        return self._receptacles.add(
            Receptacle(
                id="",
                state=ReceptacleState.DROPPED,
                virtue=self._rng.choice(list(Virtue)),
                rarity=rarity,
                value=self._rng.randint(low, high),
                is_generated=True,
                is_secret=False,
                friend_name=None,
                reward_text=None,
                content=self._content.fetch(rarity),
                treasure_id=None,
                created_at=self._now(),
            )
        )

    # --- discarding ---

    def discard(self, treasure_id: str) -> Treasure | None:
        """Lose a treasure: once per day across all slots (ARCHITECTURE §7.6).

        Its receptacles go back to the pool untouched; a fresh treasure takes
        the slot immediately.
        """
        treasure = self._get_treasure(treasure_id)
        today = self._now().astimezone(self._tz).date()
        if self._meta.get_last_discard_date() == today:
            raise DiscardAlreadyUsed("the once-a-day discard has already been used today")

        for receptacle in self.contents(treasure):
            receptacle.state = ReceptacleState.IN_POOL
            receptacle.treasure_id = None
            self._receptacles.update(receptacle)

        self._treasures.delete(treasure.id)
        self._meta.set_last_discard_date(today)
        return self.generate(treasure.slot)

    def _get_treasure(self, treasure_id: str) -> Treasure:
        for treasure in self._treasures.get_all():
            if treasure.id == treasure_id:
                return treasure
        raise NotFound(f"no treasure with id {treasure_id}")
