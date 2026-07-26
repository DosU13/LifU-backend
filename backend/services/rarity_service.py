from core.constants import RARITY_RATIO, RARITY_RATIO_TOTAL
from core.entities import Receptacle
from core.enums import ReceptacleRarity, ReceptacleState
from repos.interfaces import ReceptacleRepository

# Most common first — also the tie-break order when fractional remainders are equal.
_RARITIES_COMMON_FIRST: tuple[ReceptacleRarity, ...] = (
    ReceptacleRarity.CHEST,
    ReceptacleRarity.SAFE,
    ReceptacleRarity.VAULT,
    ReceptacleRarity.SANCTUM,
)


def apportion(n: int) -> dict[ReceptacleRarity, int]:
    """Split `n` slots across Chest:Safe:Vault:Sanctum = 27:9:3:1 (ARCHITECTURE §7.4).

    Largest-remainder (Hamilton) apportionment, done in exact integer
    arithmetic so results never drift with floating point. Ties in the
    fractional remainder go to the more common rarity (Chest first).

    Worked examples: n=1 -> 1 Chest; n=4 -> 3C+1 Safe; n=14 -> 10C+3S+1 Vault;
    n=18 -> first Sanctum appears; n=40 -> exactly 27/9/3/1.
    """
    counts = {r: (n * RARITY_RATIO[r]) // RARITY_RATIO_TOTAL for r in _RARITIES_COMMON_FIRST}
    leftover = n - sum(counts.values())
    if leftover:

        def rank_key(index_and_rarity: tuple[int, ReceptacleRarity]) -> tuple[int, int]:
            index, rarity = index_and_rarity
            remainder = (n * RARITY_RATIO[rarity]) % RARITY_RATIO_TOTAL
            return (-remainder, index)  # bigger remainder first, then more common first

        ranked = sorted(enumerate(_RARITIES_COMMON_FIRST), key=rank_key)
        for _, rarity in ranked[:leftover]:
            counts[rarity] += 1
    return counts


def _sort_key(receptacle: Receptacle):
    # Highest value first; older wins the rarer slot on ties; id as final tiebreak.
    return (-receptacle.value, receptacle.created_at, receptacle.id)


class RarityService:
    def __init__(self, receptacles: ReceptacleRepository) -> None:
        self._receptacles = receptacles

    def recalculate(self) -> None:
        """Reassign rarities across all non-generated receptacles.

        Opened receptacles keep their frozen rarity but still occupy their
        rank's slot — so an opened one sitting at rank 1 consumes the Sanctum
        slot, and live counts can legitimately deviate from 27:9:3:1.
        Idempotent: running it twice in a row changes nothing.
        """
        receptacles = sorted(self._receptacles.list_non_generated(), key=_sort_key)
        counts = apportion(len(receptacles))

        rank = 0
        for rarity in reversed(_RARITIES_COMMON_FIRST):  # rarest slots go to the top ranks
            for _ in range(counts[rarity]):
                receptacle = receptacles[rank]
                rank += 1
                if receptacle.state is ReceptacleState.OPENED:
                    continue  # frozen — occupies the slot without taking its rarity
                if receptacle.rarity is not rarity:
                    receptacle.rarity = rarity
                    self._receptacles.update(receptacle)
