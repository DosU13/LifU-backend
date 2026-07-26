import { describe, expect, it } from 'vitest'

import {
  COMBINED_PAIRS,
  VIRTUE_ELEMENT,
  collectableRarityFor,
  isCombinedElement,
  keyForReceptacle,
  nextRarity,
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
