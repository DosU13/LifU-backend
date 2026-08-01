import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { collectableIcon, iconForStockKey, receptacleIcon } from '../ui/Icon'
import type { CollectableRarity, Element, ReceptacleRarity, Virtue } from '../types'

/**
 * Every icon path the UI can produce must resolve to a file that exists.
 *
 * The paths are built by lowercasing enum names rather than from a lookup
 * table, which is only safe if the naming convention actually holds across
 * all 156. A typo in one element name would otherwise ship as a broken image
 * that nobody notices until that rarity is first earned.
 */

const PUBLIC = join(process.cwd(), 'public')

const ELEMENTS: Element[] = [
  'SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH', 'HARMONY',
  'GROWTH', 'FORGE', 'DUST', 'MOUNTAIN', 'STEAM',
  'MIST', 'OCEAN', 'LIGHTNING', 'SUN', 'WIND',
]

const COLLECTABLE_RARITIES: CollectableRarity[] = [
  'FRAGMENT', 'SHARD', 'CRYSTAL', 'ESSENCE', 'SOUL', 'CORE',
]

const VIRTUES: Virtue[] = [
  'NURTURING', 'DETERMINATION', 'ADAPTABILITY', 'PRESENCE', 'TRANSFORMATION',
  'REFLECTION', 'SERENITY', 'INSPIRATION', 'VITALITY', 'FREEDOM',
]

const RECEPTACLE_RARITIES: ReceptacleRarity[] = [
  'POUCH', 'SACK', 'CHEST', 'SAFE', 'VAULT', 'SANCTUM',
]

const onDisk = (url: string) => existsSync(join(PUBLIC, url))

describe('collectable icons', () => {
  it('covers every element and rarity', () => {
    expect(ELEMENTS.length * COLLECTABLE_RARITIES.length).toBe(96)
  })

  const missing: string[] = []
  for (const element of ELEMENTS) {
    for (const rarity of COLLECTABLE_RARITIES) {
      it(`${element} ${rarity} exists`, () => {
        const url = collectableIcon(element, rarity)
        if (!onDisk(url)) missing.push(url)
        expect(onDisk(url), `missing ${url}`).toBe(true)
      })
    }
  }
})

describe('receptacle icons', () => {
  it('covers every virtue and rarity', () => {
    expect(VIRTUES.length * RECEPTACLE_RARITIES.length).toBe(60)
  })

  for (const virtue of VIRTUES) {
    for (const rarity of RECEPTACLE_RARITIES) {
      it(`${rarity} of ${virtue} exists`, () => {
        const url = receptacleIcon(virtue, rarity)
        expect(onDisk(url), `missing ${url}`).toBe(true)
      })
    }
  }
})

describe('stock keys', () => {
  it('maps a backend stock key straight to its icon', () => {
    // serialize_stocks emits exactly this shape.
    expect(iconForStockKey('FIRE_SHARD')).toBe('/icons/collectables/fire_shard.png')
    expect(onDisk(iconForStockKey('FIRE_SHARD'))).toBe(true)
  })

  it('agrees with the element/rarity builder for every combination', () => {
    for (const element of ELEMENTS) {
      for (const rarity of COLLECTABLE_RARITIES) {
        expect(iconForStockKey(`${element}_${rarity}`)).toBe(collectableIcon(element, rarity))
      }
    }
  })
})
