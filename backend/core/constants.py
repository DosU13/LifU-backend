from core.enums import ElementKind, ReceptacleRarity

# --- Task valuation (ARCHITECTURE §7.1) ---
VIRTUE_TUNER = 1.0

# --- Collectable merging (ARCHITECTURE §7.2, §7.3) ---
MERGE_INPUT = 3
MERGE_OUTPUT = 1

HARMONY_BASE_YIELD = 5
HARMONY_EXTRA_CHANCE = 0.5
HARMONY_EXTRA_CAP = 64

# --- Sell price (ARCHITECTURE §4): coins = FE(element) * 3^rarity_index ---
FE_BASE = 1
FE_HARMONY = 1
FE_COMBINED = 3

FE_BY_KIND: dict[ElementKind, int] = {
    ElementKind.BASE: FE_BASE,
    ElementKind.HARMONY: FE_HARMONY,
    ElementKind.COMBINED: FE_COMBINED,
}

# --- Rarity recalculation quotas (ARCHITECTURE §7.4): Chest:Safe:Vault:Sanctum = 27:9:3:1 ---
RARITY_RATIO: dict[ReceptacleRarity, int] = {
    ReceptacleRarity.CHEST: 27,
    ReceptacleRarity.SAFE: 9,
    ReceptacleRarity.VAULT: 3,
    ReceptacleRarity.SANCTUM: 1,
}
RARITY_RATIO_TOTAL = sum(RARITY_RATIO.values())  # 40

# --- Treasure drop table, rarest first (ARCHITECTURE §7.6) ---
DROP_CHANCES: dict[ReceptacleRarity, float] = {
    ReceptacleRarity.SANCTUM: 1 / 243,
    ReceptacleRarity.VAULT: 1 / 81,
    ReceptacleRarity.SAFE: 1 / 27,
    ReceptacleRarity.CHEST: 1 / 9,
    ReceptacleRarity.SACK: 1 / 3,
    ReceptacleRarity.POUCH: 1.0,
}

# Per-treasure pity counters; die with the treasure (owner's explicit choice).
PITY_THRESHOLDS: dict[ReceptacleRarity, int] = {
    ReceptacleRarity.VAULT: 27,
    ReceptacleRarity.SANCTUM: 81,
}

TREASURE_COUNT = 3
TREASURE_SIZE_MIN = 5
TREASURE_SIZE_MAX = 10

# Random coin value range for generated (Pouch/Sack) receptacles.
POUCH_VALUE_RANGE: tuple[int, int] = (1, 15)
SACK_VALUE_RANGE: tuple[int, int] = (10, 40)

# Secret gifts are always worth more than 50 (ARCHITECTURE §7.5 / spec rule).
SECRET_MIN_VALUE = 51

# One discard ("lose the treasure") per day, across all slots combined.
DISCARDS_PER_DAY = 1

# AI response validation retry budget (ARCHITECTURE §8).
AI_MAX_RETRIES = 2
