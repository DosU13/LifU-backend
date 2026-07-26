from core.constants import FE_BY_KIND
from core.enums import (
    CollectableRarity,
    Element,
    ReceptacleRarity,
    TaskVirtue,
    Virtue,
    element_kind,
)

# Base element <-> task virtue — drives the fragment-award formula (ARCHITECTURE §7.1).
ELEMENT_TASK_VIRTUE: dict[Element, TaskVirtue] = {
    Element.SPACE: TaskVirtue.AWARENESS,
    Element.AIR: TaskVirtue.CURIOSITY,
    Element.FIRE: TaskVirtue.WILLPOWER,
    Element.WATER: TaskVirtue.COMPASSION,
    Element.EARTH: TaskVirtue.DISCIPLINE,
}
TASK_VIRTUE_ELEMENT: dict[TaskVirtue, Element] = {v: k for k, v in ELEMENT_TASK_VIRTUE.items()}

# Combined element composition — two base elements (same rarity) + one Harmony (ARCHITECTURE §7.3).
COMBINED_ELEMENT: dict[frozenset[Element], Element] = {
    frozenset({Element.EARTH, Element.WATER}): Element.GROWTH,
    frozenset({Element.EARTH, Element.FIRE}): Element.FORGE,
    frozenset({Element.EARTH, Element.AIR}): Element.DUST,
    frozenset({Element.EARTH, Element.SPACE}): Element.MOUNTAIN,
    frozenset({Element.WATER, Element.FIRE}): Element.STEAM,
    frozenset({Element.WATER, Element.AIR}): Element.MIST,
    frozenset({Element.WATER, Element.SPACE}): Element.OCEAN,
    frozenset({Element.FIRE, Element.AIR}): Element.LIGHTNING,
    frozenset({Element.FIRE, Element.SPACE}): Element.SUN,
    frozenset({Element.AIR, Element.SPACE}): Element.WIND,
}


def combined_element(a: Element, b: Element) -> Element:
    """The combined element produced by merging base elements a and b. Order-independent."""
    try:
        return COMBINED_ELEMENT[frozenset({a, b})]
    except KeyError as exc:
        raise ValueError(f"{a} + {b} is not a valid base-element pair") from exc


# Virtue <-> combined element — 1:1, drives the receptacle key lookup (ARCHITECTURE §3/§7.5).
VIRTUE_ELEMENT: dict[Virtue, Element] = {
    Virtue.NURTURING: Element.GROWTH,
    Virtue.DETERMINATION: Element.FORGE,
    Virtue.ADAPTABILITY: Element.DUST,
    Virtue.PRESENCE: Element.MOUNTAIN,
    Virtue.TRANSFORMATION: Element.STEAM,
    Virtue.REFLECTION: Element.MIST,
    Virtue.SERENITY: Element.OCEAN,
    Virtue.INSPIRATION: Element.LIGHTNING,
    Virtue.VITALITY: Element.SUN,
    Virtue.FREEDOM: Element.WIND,
}
ELEMENT_VIRTUE: dict[Element, Virtue] = {v: k for k, v in VIRTUE_ELEMENT.items()}


def key_rarity_for(receptacle_rarity: ReceptacleRarity) -> CollectableRarity:
    """Receptacle rarity and collectable rarity share the same ordinal index."""
    return CollectableRarity(receptacle_rarity.value)


def receptacle_rarity_for(collectable_rarity: CollectableRarity) -> ReceptacleRarity:
    return ReceptacleRarity(collectable_rarity.value)


def key_for_receptacle(
    virtue: Virtue, rarity: ReceptacleRarity
) -> tuple[Element, CollectableRarity]:
    """The exact collectable (element, rarity) required to open a receptacle.

    Example: a Safe of Serenity (SERENITY, SAFE) needs one Ocean Essence
    (OCEAN, ESSENCE).
    """
    return VIRTUE_ELEMENT[virtue], key_rarity_for(rarity)


def sell_price(element: Element, rarity: CollectableRarity) -> int:
    """Coins earned selling one collectable (ARCHITECTURE §4).

    price = FE(element) * 3^rarity_index, where FE (fragment-equivalent at
    FRAGMENT tier) is 1 for base/harmony elements and 3 for combined elements.
    """
    fe = FE_BY_KIND[element_kind(element)]
    return fe * (3**rarity.value)
