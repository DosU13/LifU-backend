import pytest

from core.enums import CollectableRarity, Element, ReceptacleRarity, TaskVirtue, Virtue
from core.mappings import (
    COMBINED_ELEMENT,
    ELEMENT_TASK_VIRTUE,
    ELEMENT_VIRTUE,
    TASK_VIRTUE_ELEMENT,
    VIRTUE_ELEMENT,
    combined_element,
    key_for_receptacle,
    key_rarity_for,
    receptacle_rarity_for,
    sell_price,
)


def test_element_task_virtue_table_is_exact():
    assert ELEMENT_TASK_VIRTUE == {
        Element.SPACE: TaskVirtue.AWARENESS,
        Element.AIR: TaskVirtue.CURIOSITY,
        Element.FIRE: TaskVirtue.WILLPOWER,
        Element.WATER: TaskVirtue.COMPASSION,
        Element.EARTH: TaskVirtue.DISCIPLINE,
    }
    assert TASK_VIRTUE_ELEMENT == {v: k for k, v in ELEMENT_TASK_VIRTUE.items()}
    assert len(TASK_VIRTUE_ELEMENT) == 5


def test_combined_element_table_is_exact_and_has_10_entries():
    assert len(COMBINED_ELEMENT) == 10
    expected = {
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
    assert COMBINED_ELEMENT == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (Element.EARTH, Element.WATER, Element.GROWTH),
        (Element.EARTH, Element.FIRE, Element.FORGE),
        (Element.EARTH, Element.AIR, Element.DUST),
        (Element.EARTH, Element.SPACE, Element.MOUNTAIN),
        (Element.WATER, Element.FIRE, Element.STEAM),
        (Element.WATER, Element.AIR, Element.MIST),
        (Element.WATER, Element.SPACE, Element.OCEAN),
        (Element.FIRE, Element.AIR, Element.LIGHTNING),
        (Element.FIRE, Element.SPACE, Element.SUN),
        (Element.AIR, Element.SPACE, Element.WIND),
    ],
)
def test_combined_element_is_order_independent(a, b, expected):
    assert combined_element(a, b) == expected
    assert combined_element(b, a) == expected


def test_combined_element_rejects_invalid_pairs():
    with pytest.raises(ValueError):
        combined_element(Element.EARTH, Element.EARTH)
    with pytest.raises(ValueError):
        combined_element(Element.EARTH, Element.GROWTH)
    with pytest.raises(ValueError):
        combined_element(Element.HARMONY, Element.FIRE)


def test_virtue_element_table_is_exact():
    assert VIRTUE_ELEMENT == {
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
    assert ELEMENT_VIRTUE == {v: k for k, v in VIRTUE_ELEMENT.items()}
    assert len(VIRTUE_ELEMENT) == 10


def test_rarity_index_round_trip_for_all_6_rarities():
    for cr in CollectableRarity:
        rr = receptacle_rarity_for(cr)
        assert rr.value == cr.value
        assert key_rarity_for(rr) == cr


def test_safe_of_serenity_needs_ocean_essence():
    """The explicit example from SPEC.md: Safe of Serenity opens with one Ocean Essence."""
    element, rarity = key_for_receptacle(Virtue.SERENITY, ReceptacleRarity.SAFE)
    assert element == Element.OCEAN
    assert rarity == CollectableRarity.ESSENCE


@pytest.mark.parametrize(
    ("virtue", "rarity", "element", "collectable_rarity"),
    [
        (Virtue.NURTURING, ReceptacleRarity.POUCH, Element.GROWTH, CollectableRarity.FRAGMENT),
        (Virtue.DETERMINATION, ReceptacleRarity.SACK, Element.FORGE, CollectableRarity.SHARD),
        (Virtue.ADAPTABILITY, ReceptacleRarity.CHEST, Element.DUST, CollectableRarity.CRYSTAL),
        (Virtue.PRESENCE, ReceptacleRarity.SAFE, Element.MOUNTAIN, CollectableRarity.ESSENCE),
        (Virtue.TRANSFORMATION, ReceptacleRarity.VAULT, Element.STEAM, CollectableRarity.SOUL),
        (Virtue.FREEDOM, ReceptacleRarity.SANCTUM, Element.WIND, CollectableRarity.CORE),
    ],
)
def test_key_for_receptacle_matrix(virtue, rarity, element, collectable_rarity):
    assert key_for_receptacle(virtue, rarity) == (element, collectable_rarity)


# --- Sell price: the 12-cell table from ARCHITECTURE §4 ---

BASE_ROW = [1, 3, 9, 27, 81, 243]
COMBINED_ROW = [3, 9, 27, 81, 243, 729]


@pytest.mark.parametrize("rarity_index", range(6))
def test_sell_price_base_and_harmony_row(rarity_index):
    rarity = CollectableRarity(rarity_index)
    expected = BASE_ROW[rarity_index]
    for e in (Element.SPACE, Element.AIR, Element.FIRE, Element.WATER, Element.EARTH):
        assert sell_price(e, rarity) == expected
    assert sell_price(Element.HARMONY, rarity) == expected


@pytest.mark.parametrize("rarity_index", range(6))
def test_sell_price_combined_row(rarity_index):
    rarity = CollectableRarity(rarity_index)
    expected = COMBINED_ROW[rarity_index]
    combined = [
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
    ]
    for e in combined:
        assert sell_price(e, rarity) == expected
