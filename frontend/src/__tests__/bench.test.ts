import { describe, expect, it } from 'vitest'

import { COMBINED_PAIRS } from '../domain'
import { detectOp, maxRepeats } from '../layouts/bench'
import type { BenchItem } from '../layouts/bench'
import { stockKey } from '../types'
import type { CollectableRarity, Element, Receptacle, Stocks } from '../types'

const c = (element: Element, rarity: CollectableRarity = 'FRAGMENT'): BenchItem => ({
  type: 'collectable',
  element,
  rarity,
})

function receptacle(overrides: Partial<Receptacle> = {}): Receptacle {
  return {
    id: 'r1',
    state: 'DROPPED',
    virtue: 'SERENITY',
    rarity: 'SAFE',
    is_generated: false,
    is_secret: false,
    friend_name: null,
    created_at: '2026-01-01T00:00:00Z',
    opened_at: null,
    key_needed: { element: 'OCEAN', rarity: 'ESSENCE' },
    value: null,
    reward_text: null,
    content: null,
    ...overrides,
  }
}

const stocks = (entries: Record<string, number> = {}): Stocks => entries

describe('merge up', () => {
  it('takes three of exactly the same thing', () => {
    const op = detectOp([c('FIRE'), c('FIRE'), c('FIRE')], stocks())
    expect(op.kind).toBe('merge')
    expect(op.label).toBe('Merge up → Fire Shard')
  })

  it('names the right next rarity at every step', () => {
    const ladder: [CollectableRarity, string][] = [
      ['FRAGMENT', 'Shard'],
      ['SHARD', 'Crystal'],
      ['CRYSTAL', 'Essence'],
      ['ESSENCE', 'Soul'],
      ['SOUL', 'Core'],
    ]
    for (const [rarity, expected] of ladder) {
      const op = detectOp([c('FIRE', rarity), c('FIRE', rarity), c('FIRE', rarity)], stocks())
      expect(op.label).toBe(`Merge up → Fire ${expected}`)
    }
  })

  it('refuses a Core, which is already the top', () => {
    const op = detectOp([c('FIRE', 'CORE'), c('FIRE', 'CORE'), c('FIRE', 'CORE')], stocks())
    expect(op.kind).toBe('blocked')
    expect(op.label).toBe('Already a Core')
  })

  it('explains when the count is wrong rather than going quiet', () => {
    const op = detectOp([c('FIRE'), c('FIRE')], stocks())
    expect(op.kind).toBe('blocked')
    expect(op).toHaveProperty('reason', expect.stringContaining('three of the same'))
  })

  it('works for combined elements too', () => {
    const op = detectOp([c('OCEAN'), c('OCEAN'), c('OCEAN')], stocks())
    expect(op.kind).toBe('merge')
    expect(op.label).toBe('Merge up → Ocean Shard')
  })
})

describe('harmony merge', () => {
  it('takes one of each base element', () => {
    const op = detectOp(
      [c('SPACE'), c('AIR'), c('FIRE'), c('WATER'), c('EARTH')],
      stocks(),
    )
    expect(op.kind).toBe('harmony')
    expect(op.label).toBe('Harmony merge')
  })

  it('works at any rarity, as long as they match', () => {
    const op = detectOp(
      ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH'].map((e) => c(e as Element, 'CRYSTAL')),
      stocks(),
    )
    expect(op.kind).toBe('harmony')
  })

  it('rejects a mixed-rarity set', () => {
    const items = ['SPACE', 'AIR', 'FIRE', 'WATER'].map((e) => c(e as Element))
    items.push(c('EARTH', 'SHARD'))
    const op = detectOp(items, stocks())
    expect(op.kind).toBe('blocked')
    expect(op).toHaveProperty('reason', expect.stringContaining('same rarity'))
  })

  it('does not fire on four base elements', () => {
    const op = detectOp(
      ['SPACE', 'AIR', 'FIRE', 'WATER'].map((e) => c(e as Element)),
      stocks(),
    )
    expect(op.kind).toBe('blocked')
  })
})

describe('combine', () => {
  it('resolves every one of the ten pairs', () => {
    // If this drifts from core/mappings.py the bench starts promising things
    // the server will refuse, so all ten are pinned rather than sampled.
    expect(COMBINED_PAIRS).toHaveLength(10)

    for (const { a, b, result } of COMBINED_PAIRS) {
      const op = detectOp([c(a), c(b), c('HARMONY')], stocks())
      expect(op.kind, `${a}+${b}`).toBe('combine')
      expect(op.label).toBe(`Combine → ${result[0]}${result.slice(1).toLowerCase()}`)
    }
  })

  it('is order-independent', () => {
    const forward = detectOp([c('EARTH'), c('WATER'), c('HARMONY')], stocks())
    const reverse = detectOp([c('WATER'), c('EARTH'), c('HARMONY')], stocks())
    expect(forward.label).toBe(reverse.label)
    expect(forward.label).toBe('Combine → Growth')
  })

  it('needs two different base elements', () => {
    const op = detectOp([c('FIRE'), c('FIRE'), c('HARMONY')], stocks())
    expect(op.kind).toBe('blocked')
  })

  it('refuses more than one harmony', () => {
    const op = detectOp([c('HARMONY'), c('HARMONY'), c('FIRE')], stocks())
    expect(op.kind).toBe('blocked')
    expect(op).toHaveProperty('reason', expect.stringContaining('single Harmony'))
  })

  it('refuses a combined element as an ingredient', () => {
    const op = detectOp([c('OCEAN'), c('FIRE'), c('HARMONY')], stocks())
    expect(op.kind).toBe('blocked')
  })
})

describe('opening a receptacle', () => {
  it('offers to open when the key is held', () => {
    const held = stocks({ [stockKey('OCEAN', 'ESSENCE')]: 2 })
    const op = detectOp([{ type: 'receptacle', receptacle: receptacle() }], held)

    expect(op.kind).toBe('open')
    expect(op.label).toBe('Open it')
  })

  it('names the missing key instead of just refusing', () => {
    const op = detectOp([{ type: 'receptacle', receptacle: receptacle() }], stocks())

    expect(op.kind).toBe('blocked')
    expect(op.label).toBe('No key')
    expect(op).toHaveProperty('reason', expect.stringContaining('Ocean Essence'))
  })

  it('derives the key from virtue and rarity, matching key_for_receptacle', () => {
    // Vault of Inspiration ⇒ Lightning Soul.
    const r = receptacle({ virtue: 'INSPIRATION', rarity: 'VAULT' })
    const op = detectOp([{ type: 'receptacle', receptacle: r }], stocks())
    expect(op).toHaveProperty('reason', expect.stringContaining('Lightning Soul'))
  })

  it('will not open alongside anything else', () => {
    const held = stocks({ [stockKey('OCEAN', 'ESSENCE')]: 1 })
    const op = detectOp(
      [{ type: 'receptacle', receptacle: receptacle() }, c('FIRE')],
      held,
    )
    expect(op.kind).toBe('blocked')
    expect(op).toHaveProperty('reason', expect.stringContaining('opens on its own'))
  })
})

describe('empty bench', () => {
  it('invites rather than scolds', () => {
    const op = detectOp([], stocks())
    expect(op.kind).toBe('blocked')
    expect(op.label).toBe('Merge')
  })
})

describe('maxRepeats', () => {
  it('counts how many merges the hoard can actually pay for', () => {
    const held = stocks({ [stockKey('FIRE', 'FRAGMENT')]: 10 })
    const op = detectOp([c('FIRE'), c('FIRE'), c('FIRE')], held)
    expect(maxRepeats(op, held)).toBe(3) // 10 / 3
  })

  it('is limited by the scarcest base element for harmony', () => {
    const held = stocks({
      [stockKey('SPACE', 'FRAGMENT')]: 9,
      [stockKey('AIR', 'FRAGMENT')]: 4,
      [stockKey('FIRE', 'FRAGMENT')]: 7,
      [stockKey('WATER', 'FRAGMENT')]: 2,
      [stockKey('EARTH', 'FRAGMENT')]: 8,
    })
    const op = detectOp(
      ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH'].map((e) => c(e as Element)),
      held,
    )
    expect(maxRepeats(op, held)).toBe(2)
  })

  it('is limited by the harmony on hand when combining', () => {
    const held = stocks({
      [stockKey('EARTH', 'FRAGMENT')]: 5,
      [stockKey('WATER', 'FRAGMENT')]: 5,
      [stockKey('HARMONY', 'FRAGMENT')]: 1,
    })
    const op = detectOp([c('EARTH'), c('WATER'), c('HARMONY')], held)
    expect(maxRepeats(op, held)).toBe(1)
  })

  it('is zero when nothing can be made', () => {
    expect(maxRepeats(detectOp([], stocks()), stocks())).toBe(0)
  })
})
