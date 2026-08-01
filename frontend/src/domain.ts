// Display-side mirror of backend/core/mappings.py. The server is always the
// authority; these tables exist so the UI can explain requirements ("this Safe
// needs an Ocean Essence") without a round trip.

import {
  COLLECTABLE_RARITIES,
  RECEPTACLE_RARITIES,
  type CollectableRarity,
  type Element,
  type ReceptacleRarity,
  type TaskVirtue,
  type Virtue,
} from './types'

/**
 * Which virtue each base element is paid for — mirrors ELEMENT_TASK_VIRTUE in
 * core/mappings.py. Only the five base elements are earned from tasks; the
 * rest are crafted, so they never appear here.
 */
export const ELEMENT_TASK_VIRTUE: Partial<Record<Element, TaskVirtue>> = {
  SPACE: 'AWARENESS',
  AIR: 'CURIOSITY',
  FIRE: 'WILLPOWER',
  WATER: 'COMPASSION',
  EARTH: 'DISCIPLINE',
}

export const ELEMENT_EMOJI: Record<Element, string> = {
  SPACE: '🌌',
  AIR: '🌬️',
  FIRE: '🔥',
  WATER: '💧',
  EARTH: '🌍',
  HARMONY: '✨',
  GROWTH: '🌱',
  FORGE: '⚒️',
  DUST: '🌫️',
  MOUNTAIN: '⛰️',
  STEAM: '☁️',
  MIST: '🌁',
  OCEAN: '🌊',
  LIGHTNING: '⚡',
  SUN: '☀️',
  WIND: '🌪️',
}

/** Each virtue unlocks with its paired combined element. */
export const VIRTUE_ELEMENT: Record<Virtue, Element> = {
  NURTURING: 'GROWTH',
  DETERMINATION: 'FORGE',
  ADAPTABILITY: 'DUST',
  PRESENCE: 'MOUNTAIN',
  TRANSFORMATION: 'STEAM',
  REFLECTION: 'MIST',
  SERENITY: 'OCEAN',
  INSPIRATION: 'LIGHTNING',
  VITALITY: 'SUN',
  FREEDOM: 'WIND',
}

/** The two base elements that combine into each combined element. */
export const COMBINED_PAIRS: ReadonlyArray<{ a: Element; b: Element; result: Element }> = [
  { a: 'EARTH', b: 'WATER', result: 'GROWTH' },
  { a: 'EARTH', b: 'FIRE', result: 'FORGE' },
  { a: 'EARTH', b: 'AIR', result: 'DUST' },
  { a: 'EARTH', b: 'SPACE', result: 'MOUNTAIN' },
  { a: 'WATER', b: 'FIRE', result: 'STEAM' },
  { a: 'WATER', b: 'AIR', result: 'MIST' },
  { a: 'WATER', b: 'SPACE', result: 'OCEAN' },
  { a: 'FIRE', b: 'AIR', result: 'LIGHTNING' },
  { a: 'FIRE', b: 'SPACE', result: 'SUN' },
  { a: 'AIR', b: 'SPACE', result: 'WIND' },
]

/** Receptacle and collectable rarities share an ordinal: Safe <-> Essence. */
export function collectableRarityFor(rarity: ReceptacleRarity): CollectableRarity {
  const index = RECEPTACLE_RARITIES.indexOf(rarity)
  const match = COLLECTABLE_RARITIES[index]
  if (!match) throw new Error(`unknown receptacle rarity: ${rarity}`)
  return match
}

/** The exact collectable that opens a receptacle: a Safe of Serenity needs an Ocean Essence. */
export function keyForReceptacle(
  virtue: Virtue,
  rarity: ReceptacleRarity,
): { element: Element; rarity: CollectableRarity } {
  return { element: VIRTUE_ELEMENT[virtue], rarity: collectableRarityFor(rarity) }
}

const BASE_OR_HARMONY_FE = 1
const COMBINED_FE = 3

export function isBaseElement(element: Element): boolean {
  return ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH'].includes(element)
}

export function isCombinedElement(element: Element): boolean {
  return element !== 'HARMONY' && !isBaseElement(element)
}

/** Coins earned selling one collectable: FE * 3^rarityIndex (ARCHITECTURE §4). */
export function sellPrice(element: Element, rarity: CollectableRarity): number {
  const fe = isCombinedElement(element) ? COMBINED_FE : BASE_OR_HARMONY_FE
  return fe * 3 ** COLLECTABLE_RARITIES.indexOf(rarity)
}

/** The rarity a 3-to-1 merge produces, or null for Core (nothing higher exists). */
export function nextRarity(rarity: CollectableRarity): CollectableRarity | null {
  return COLLECTABLE_RARITIES[COLLECTABLE_RARITIES.indexOf(rarity) + 1] ?? null
}

export function label(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase()
}

export function elementLabel(element: Element): string {
  return `${ELEMENT_EMOJI[element]} ${label(element)}`
}
