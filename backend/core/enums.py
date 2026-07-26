from enum import Enum, IntEnum


class Element(str, Enum):
    SPACE = "SPACE"
    AIR = "AIR"
    FIRE = "FIRE"
    WATER = "WATER"
    EARTH = "EARTH"
    HARMONY = "HARMONY"
    GROWTH = "GROWTH"
    FORGE = "FORGE"
    DUST = "DUST"
    MOUNTAIN = "MOUNTAIN"
    STEAM = "STEAM"
    MIST = "MIST"
    OCEAN = "OCEAN"
    LIGHTNING = "LIGHTNING"
    SUN = "SUN"
    WIND = "WIND"


BASE_ELEMENTS: tuple[Element, ...] = (
    Element.SPACE,
    Element.AIR,
    Element.FIRE,
    Element.WATER,
    Element.EARTH,
)

COMBINED_ELEMENTS: tuple[Element, ...] = (
    Element.GROWTH,
    Element.FORGE,
    Element.DUST,
    Element.MOUNTAIN,
    Element.STEAM,
    Element.MIST,
    Element.OCEAN,
    Element.LIGHTNING,
    Element.SUN,
    Element.WIND,
)


class ElementKind(str, Enum):
    BASE = "BASE"
    HARMONY = "HARMONY"
    COMBINED = "COMBINED"


def element_kind(element: Element) -> ElementKind:
    if element in BASE_ELEMENTS:
        return ElementKind.BASE
    if element is Element.HARMONY:
        return ElementKind.HARMONY
    return ElementKind.COMBINED


class CollectableRarity(IntEnum):
    FRAGMENT = 0
    SHARD = 1
    CRYSTAL = 2
    ESSENCE = 3
    SOUL = 4
    CORE = 5


class TaskVirtue(str, Enum):
    AWARENESS = "AWARENESS"
    CURIOSITY = "CURIOSITY"
    WILLPOWER = "WILLPOWER"
    COMPASSION = "COMPASSION"
    DISCIPLINE = "DISCIPLINE"


class Virtue(str, Enum):
    NURTURING = "NURTURING"
    DETERMINATION = "DETERMINATION"
    ADAPTABILITY = "ADAPTABILITY"
    PRESENCE = "PRESENCE"
    TRANSFORMATION = "TRANSFORMATION"
    REFLECTION = "REFLECTION"
    SERENITY = "SERENITY"
    INSPIRATION = "INSPIRATION"
    VITALITY = "VITALITY"
    FREEDOM = "FREEDOM"


class ReceptacleRarity(IntEnum):
    POUCH = 0
    SACK = 1
    CHEST = 2
    SAFE = 3
    VAULT = 4
    SANCTUM = 5


class ReceptacleState(str, Enum):
    IN_POOL = "IN_POOL"
    IN_TREASURE = "IN_TREASURE"
    DROPPED = "DROPPED"
    OPENED = "OPENED"


class GeneratedKind(str, Enum):
    QUOTE = "QUOTE"
    FACT = "FACT"
    MUSIC = "MUSIC"
    ART = "ART"
