from core.constants import (
    AI_MAX_RETRIES,
    DISCARDS_PER_DAY,
    DROP_CHANCES,
    HARMONY_BASE_YIELD,
    HARMONY_EXTRA_CAP,
    HARMONY_EXTRA_CHANCE,
    MERGE_INPUT,
    MERGE_OUTPUT,
    PITY_THRESHOLDS,
    POUCH_VALUE_RANGE,
    RARITY_RATIO,
    RARITY_RATIO_TOTAL,
    SACK_VALUE_RANGE,
    SECRET_MIN_VALUE,
    TREASURE_COUNT,
    TREASURE_SIZE_MAX,
    TREASURE_SIZE_MIN,
    VIRTUE_TUNER,
)
from core.enums import ReceptacleRarity


def test_merge_and_harmony_constants():
    assert MERGE_INPUT == 3
    assert MERGE_OUTPUT == 1
    assert HARMONY_BASE_YIELD == 5
    assert HARMONY_EXTRA_CHANCE == 0.5
    assert HARMONY_EXTRA_CAP == 64
    assert VIRTUE_TUNER == 1.0


def test_rarity_ratio_is_27_9_3_1_and_sums_to_40():
    assert RARITY_RATIO == {
        ReceptacleRarity.CHEST: 27,
        ReceptacleRarity.SAFE: 9,
        ReceptacleRarity.VAULT: 3,
        ReceptacleRarity.SANCTUM: 1,
    }
    assert RARITY_RATIO_TOTAL == 40


def test_drop_chances_table_matches_spec():
    assert DROP_CHANCES[ReceptacleRarity.POUCH] == 1.0
    assert DROP_CHANCES[ReceptacleRarity.SACK] == 1 / 3
    assert DROP_CHANCES[ReceptacleRarity.CHEST] == 1 / 9
    assert DROP_CHANCES[ReceptacleRarity.SAFE] == 1 / 27
    assert DROP_CHANCES[ReceptacleRarity.VAULT] == 1 / 81
    assert DROP_CHANCES[ReceptacleRarity.SANCTUM] == 1 / 243


def test_pity_thresholds():
    assert PITY_THRESHOLDS == {
        ReceptacleRarity.VAULT: 27,
        ReceptacleRarity.SANCTUM: 81,
    }


def test_treasure_and_value_ranges():
    assert TREASURE_COUNT == 3
    assert (TREASURE_SIZE_MIN, TREASURE_SIZE_MAX) == (5, 10)
    assert POUCH_VALUE_RANGE == (1, 15)
    assert SACK_VALUE_RANGE == (10, 40)


def test_secret_and_misc_constants():
    assert SECRET_MIN_VALUE == 51
    assert DISCARDS_PER_DAY == 1
    assert AI_MAX_RETRIES == 2
