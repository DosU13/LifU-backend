from dataclasses import dataclass

from core.constants import (
    HARMONY_BASE_YIELD,
    HARMONY_EXTRA_CAP,
    HARMONY_EXTRA_CHANCE,
    MERGE_INPUT,
    MERGE_OUTPUT,
)
from core.enums import BASE_ELEMENTS, CollectableRarity, Element
from core.errors import InvalidMerge
from core.mappings import combined_element
from core.rng import Rng
from repos.interfaces import CollectableRepository


@dataclass
class HarmonyMergeResult:
    harmony_yield: int
    extras: int


class MergerService:
    def __init__(self, collectables: CollectableRepository, rng: Rng) -> None:
        self._collectables = collectables
        self._rng = rng

    def merge_up(self, element: Element, rarity: CollectableRarity) -> CollectableRarity:
        """3 of (element, rarity) -> 1 of (element, rarity+1). Works for any element."""
        if rarity == CollectableRarity.CORE:
            raise InvalidMerge("Core is the highest rarity and cannot be merged further")
        next_rarity = CollectableRarity(rarity.value + 1)
        self._collectables.adjust(
            {
                (element, rarity): -MERGE_INPUT,
                (element, next_rarity): MERGE_OUTPUT,
            }
        )
        return next_rarity

    def merge_harmony(self, rarity: CollectableRarity) -> HarmonyMergeResult:
        """1 of each of the 5 base elements (same rarity) -> 5+ Harmony (ARCHITECTURE §7.3).

        The whole repeat-until-fail 50% extra roll is resolved server-side in
        one call; the frontend replays the build-up animation `extras` times.
        """
        extras = 0
        while extras < HARMONY_EXTRA_CAP and self._rng.random() < HARMONY_EXTRA_CHANCE:
            extras += 1
        harmony_yield = HARMONY_BASE_YIELD + extras

        deltas: dict[tuple[Element, CollectableRarity], int] = {
            (element, rarity): -1 for element in BASE_ELEMENTS
        }
        deltas[(Element.HARMONY, rarity)] = harmony_yield
        self._collectables.adjust(deltas)

        return HarmonyMergeResult(harmony_yield=harmony_yield, extras=extras)

    def combine(self, a: Element, b: Element, rarity: CollectableRarity) -> Element:
        """1 Harmony + 1 each of two distinct base elements (same rarity) -> 1 combined element."""
        try:
            result = combined_element(a, b)
        except ValueError as exc:
            raise InvalidMerge(str(exc)) from exc

        self._collectables.adjust(
            {
                (a, rarity): -1,
                (b, rarity): -1,
                (Element.HARMONY, rarity): -1,
                (result, rarity): 1,
            }
        )
        return result
