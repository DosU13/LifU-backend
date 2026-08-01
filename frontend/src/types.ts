// Mirrors the backend domain (docs/ARCHITECTURE.md §2-3). Keep in sync with
// backend/core/enums.py — these strings are the wire format.

export const BASE_ELEMENTS = ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH'] as const
export const COMBINED_ELEMENTS = [
  'GROWTH',
  'FORGE',
  'DUST',
  'MOUNTAIN',
  'STEAM',
  'MIST',
  'OCEAN',
  'LIGHTNING',
  'SUN',
  'WIND',
] as const
export const ELEMENTS = [...BASE_ELEMENTS, 'HARMONY', ...COMBINED_ELEMENTS] as const

export const COLLECTABLE_RARITIES = [
  'FRAGMENT',
  'SHARD',
  'CRYSTAL',
  'ESSENCE',
  'SOUL',
  'CORE',
] as const

export const RECEPTACLE_RARITIES = [
  'POUCH',
  'SACK',
  'CHEST',
  'SAFE',
  'VAULT',
  'SANCTUM',
] as const

export const VIRTUES = [
  'NURTURING',
  'DETERMINATION',
  'ADAPTABILITY',
  'PRESENCE',
  'TRANSFORMATION',
  'REFLECTION',
  'SERENITY',
  'INSPIRATION',
  'VITALITY',
  'FREEDOM',
] as const

export const TASK_VIRTUES = [
  'AWARENESS',
  'CURIOSITY',
  'WILLPOWER',
  'COMPASSION',
  'DISCIPLINE',
] as const

export type Element = (typeof ELEMENTS)[number]
export type CollectableRarity = (typeof COLLECTABLE_RARITIES)[number]
export type ReceptacleRarity = (typeof RECEPTACLE_RARITIES)[number]
export type Virtue = (typeof VIRTUES)[number]
export type TaskVirtue = (typeof TASK_VIRTUES)[number]
export type ReceptacleState = 'IN_POOL' | 'IN_TREASURE' | 'DROPPED' | 'OPENED'
export type GeneratedKind = 'QUOTE' | 'FACT' | 'MUSIC' | 'ART'

/** Keys are `${Element}_${CollectableRarity}`, e.g. "FIRE_SHARD". */
export type Stocks = Record<string, number>

export function stockKey(element: Element, rarity: CollectableRarity): string {
  return `${element}_${rarity}`
}

export interface KeyRequirement {
  element: Element
  rarity: CollectableRarity
}

export interface GeneratedContent {
  kind: GeneratedKind
  title: string
  url: string
  author: string
  text: string
}

export interface Receptacle {
  id: string
  state: ReceptacleState
  virtue: Virtue
  rarity: ReceptacleRarity
  is_generated: boolean
  is_secret: boolean
  friend_name: string | null
  created_at: string
  opened_at: string | null
  key_needed: KeyRequirement
  /**
   * Everything below describes the contents, so the server sends null until
   * the receptacle is OPENED — including rewards you wrote yourself. Knowing
   * both the reward and its rarity would rank your whole wishlist.
   */
  value: number | null
  reward_text: string | null
  content: GeneratedContent | null
}

/**
 * A reward as its author sees it on the admin page. Deliberately carries no
 * virtue, rarity, value or id: which receptacle it became is the surprise.
 */
export interface Reward {
  /** Null for a friend's secret gift until it has been opened. */
  text: string | null
  is_secret: boolean
  friend_name: string | null
  created_at: string
  is_opened: boolean
}

/** What a treasure shows before you buy: no values, no reward text. */
export interface TreasureContentPreview {
  virtue: Virtue
  rarity: ReceptacleRarity
  is_secret: boolean
  friend_name: string | null
}

export interface Treasure {
  id: string
  slot: number
  price: number
  pity: Record<string, number>
  contents: TreasureContentPreview[]
}

export interface Stats {
  per_day: Record<string, number>
  virtue_means: Record<TaskVirtue, number>
  streak: number
}

export interface GameState {
  coins: number
  stocks: Stocks
  treasures: Treasure[]
  dropped_receptacles: Receptacle[]
  stats: Stats
}

export interface TaskCompletion {
  task: { value: number; virtues: Record<TaskVirtue, number> }
  fragments_awarded: Partial<Record<Element, number>>
}

export interface Task {
  id: string
  text: string
  created_at: string
  value: number
  virtues: Record<TaskVirtue, number>
  fragments_awarded: Partial<Record<Element, number>>
}

export interface HarmonyResult {
  yield: number
  extras: number
  stocks: Stocks
}

export interface BuyResult {
  drop: Receptacle
  dropped_rarity: ReceptacleRarity
  was_pity: boolean
  price_paid: number
  coins: number
  pity: Record<string, number>
  treasure_gone: boolean
}

export interface OpenResult {
  receptacle: Receptacle
  coins_gained: number
  coins: number
}

export interface FriendLink {
  name: string
  url: string
}

export interface SessionInfo {
  authenticated: boolean
  is_trial: boolean
}
