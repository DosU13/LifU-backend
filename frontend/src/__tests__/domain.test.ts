import { describe, expect, it } from 'vitest'

import {
  COMBINED_PAIRS,
  VIRTUE_ELEMENT,
  collectableRarityFor,
  doshaComposition,
  isCombinedElement,
  keyForReceptacle,
  nextRarity,
  revealTier,
  sellPrice,
} from '../domain'
import { COLLECTABLE_RARITIES, RECEPTACLE_RARITIES, VIRTUES } from '../types'

describe('key derivation', () => {
  it('a Safe of Serenity needs an Ocean Essence', () => {
    expect(keyForReceptacle('SERENITY', 'SAFE')).toEqual({
      element: 'OCEAN',
      rarity: 'ESSENCE',
    })
  })

  it.each([
    ['NURTURING', 'POUCH', 'GROWTH', 'FRAGMENT'],
    ['DETERMINATION', 'SACK', 'FORGE', 'SHARD'],
    ['ADAPTABILITY', 'CHEST', 'DUST', 'CRYSTAL'],
    ['PRESENCE', 'SAFE', 'MOUNTAIN', 'ESSENCE'],
    ['TRANSFORMATION', 'VAULT', 'STEAM', 'SOUL'],
    ['FREEDOM', 'SANCTUM', 'WIND', 'CORE'],
  ] as const)('%s at %s needs %s %s', (virtue, rarity, element, keyRarity) => {
    expect(keyForReceptacle(virtue, rarity)).toEqual({ element, rarity: keyRarity })
  })

  it('covers every virtue with a distinct combined element', () => {
    const elements = VIRTUES.map((virtue) => VIRTUE_ELEMENT[virtue])
    expect(new Set(elements).size).toBe(10)
    expect(elements.every(isCombinedElement)).toBe(true)
  })

  it('maps receptacle rarities onto collectable rarities by ordinal', () => {
    RECEPTACLE_RARITIES.forEach((rarity, index) => {
      expect(collectableRarityFor(rarity)).toBe(COLLECTABLE_RARITIES[index])
    })
  })
})

describe('reveal tiers', () => {
  it('leaves the bottom half of the scale plain', () => {
    // If every payout got an effect, none of them would land as an event.
    expect(revealTier('FRAGMENT')).toBeUndefined()
    expect(revealTier('SHARD')).toBeUndefined()
    expect(revealTier('CRYSTAL')).toBeUndefined()
    expect(revealTier('POUCH')).toBeUndefined()
    expect(revealTier('SACK')).toBeUndefined()
    expect(revealTier('CHEST')).toBeUndefined()
  })

  it('escalates over the top three', () => {
    expect(revealTier('ESSENCE')).toBe('gilded')
    expect(revealTier('SOUL')).toBe('radiant')
    expect(revealTier('CORE')).toBe('mythic')
  })

  it('treats a receptacle exactly like the collectable of its ordinal', () => {
    RECEPTACLE_RARITIES.forEach((rarity, index) => {
      expect(revealTier(rarity)).toBe(revealTier(COLLECTABLE_RARITIES[index]!))
    })
  })
})

describe('dosha composition', () => {
  it('sends Space and Air to Vata alone', () => {
    expect(doshaComposition({ SPACE: 4, AIR: 6 })).toEqual({ vata: 10, pitta: 0, kapha: 0 })
  })

  it('counts water in full toward both Pitta and Kapha, not split in half', () => {
    // Owner's call: halving water would leave Pitta and Kapha drawing on one
    // and a half elements each while Vata draws on two whole ones, quietly
    // discounting the two doshas that happen to share an element.
    expect(doshaComposition({ FIRE: 5, WATER: 5, EARTH: 5 })).toEqual({
      vata: 0,
      pitta: 10,
      kapha: 10,
    })
  })

  it('returns all zeros for no history', () => {
    expect(doshaComposition({})).toEqual({ vata: 0, pitta: 0, kapha: 0 })
  })

  it('ignores combined elements and Harmony defensively', () => {
    // Tasks only ever award base fragments, but the function's input type
    // permits any element, so a combined one should not silently count.
    expect(doshaComposition({ SPACE: 2, HARMONY: 9, SUN: 9, OCEAN: 9 })).toEqual({
      vata: 2,
      pitta: 0,
      kapha: 0,
    })
  })
})

describe('sell price', () => {
  it.each([
    ['FIRE', 'FRAGMENT', 1],
    ['FIRE', 'CORE', 243],
    ['HARMONY', 'FRAGMENT', 1],
    ['HARMONY', 'SOUL', 81],
    ['OCEAN', 'FRAGMENT', 3],
    ['OCEAN', 'CORE', 729],
  ] as const)('%s %s sells for %i', (element, rarity, expected) => {
    expect(sellPrice(element, rarity)).toBe(expected)
  })
})

describe('merge targets', () => {
  it('steps up one rarity at a time', () => {
    expect(nextRarity('FRAGMENT')).toBe('SHARD')
    expect(nextRarity('SOUL')).toBe('CORE')
  })

  it('has nothing above Core', () => {
    expect(nextRarity('CORE')).toBeNull()
  })
})

describe('combine pairs', () => {
  it('lists all ten pairs, each producing a distinct element', () => {
    expect(COMBINED_PAIRS).toHaveLength(10)
    expect(new Set(COMBINED_PAIRS.map((p) => p.result)).size).toBe(10)
  })

  it('only ever combines two different base elements', () => {
    for (const pair of COMBINED_PAIRS) {
      expect(pair.a).not.toBe(pair.b)
      expect(isCombinedElement(pair.a)).toBe(false)
      expect(isCombinedElement(pair.b)).toBe(false)
    }
  })
})
