from core.enums import (
    BASE_ELEMENTS,
    COMBINED_ELEMENTS,
    CollectableRarity,
    Element,
    ElementKind,
    GeneratedKind,
    ReceptacleRarity,
    ReceptacleState,
    TaskVirtue,
    Virtue,
    element_kind,
)


def test_element_has_exactly_16_values():
    assert len(Element) == 16
    assert {e.value for e in Element} == {
        "SPACE",
        "AIR",
        "FIRE",
        "WATER",
        "EARTH",
        "HARMONY",
        "GROWTH",
        "FORGE",
        "DUST",
        "MOUNTAIN",
        "STEAM",
        "MIST",
        "OCEAN",
        "LIGHTNING",
        "SUN",
        "WIND",
    }


def test_base_and_combined_groups_partition_correctly():
    assert len(BASE_ELEMENTS) == 5
    assert len(COMBINED_ELEMENTS) == 10
    assert set(BASE_ELEMENTS) | set(COMBINED_ELEMENTS) | {Element.HARMONY} == set(Element)
    assert set(BASE_ELEMENTS).isdisjoint(COMBINED_ELEMENTS)


def test_element_kind_classifies_every_element():
    for e in BASE_ELEMENTS:
        assert element_kind(e) == ElementKind.BASE
    assert element_kind(Element.HARMONY) == ElementKind.HARMONY
    for e in COMBINED_ELEMENTS:
        assert element_kind(e) == ElementKind.COMBINED


def test_collectable_rarity_has_6_values_ordered():
    assert len(CollectableRarity) == 6
    ordered = [
        CollectableRarity.FRAGMENT,
        CollectableRarity.SHARD,
        CollectableRarity.CRYSTAL,
        CollectableRarity.ESSENCE,
        CollectableRarity.SOUL,
        CollectableRarity.CORE,
    ]
    assert ordered == sorted(ordered)
    assert CollectableRarity.FRAGMENT < CollectableRarity.CORE


def test_task_virtue_has_exactly_5_values():
    assert len(TaskVirtue) == 5
    assert {v.value for v in TaskVirtue} == {
        "AWARENESS",
        "CURIOSITY",
        "WILLPOWER",
        "COMPASSION",
        "DISCIPLINE",
    }


def test_virtue_has_exactly_10_values():
    assert len(Virtue) == 10
    assert {v.value for v in Virtue} == {
        "NURTURING",
        "DETERMINATION",
        "ADAPTABILITY",
        "PRESENCE",
        "TRANSFORMATION",
        "REFLECTION",
        "SERENITY",
        "INSPIRATION",
        "VITALITY",
        "FREEDOM",
    }


def test_receptacle_rarity_has_6_values_ordered():
    assert len(ReceptacleRarity) == 6
    ordered = [
        ReceptacleRarity.POUCH,
        ReceptacleRarity.SACK,
        ReceptacleRarity.CHEST,
        ReceptacleRarity.SAFE,
        ReceptacleRarity.VAULT,
        ReceptacleRarity.SANCTUM,
    ]
    assert ordered == sorted(ordered)
    assert ReceptacleRarity.POUCH < ReceptacleRarity.SANCTUM


def test_receptacle_state_has_4_values():
    assert len(ReceptacleState) == 4
    assert {s.value for s in ReceptacleState} == {
        "IN_POOL",
        "IN_TREASURE",
        "DROPPED",
        "OPENED",
    }


def test_generated_kind_has_4_values():
    assert len(GeneratedKind) == 4
    assert {k.value for k in GeneratedKind} == {"QUOTE", "FACT", "MUSIC", "ART"}
