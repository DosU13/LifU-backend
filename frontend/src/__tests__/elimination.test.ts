import { describe, expect, it } from 'vitest'

import { planElimination } from '../layouts/elimination'
import type { TreasureContentPreview } from '../types'

const content = (
  virtue: TreasureContentPreview['virtue'],
  rarity: TreasureContentPreview['rarity'],
): TreasureContentPreview => ({ virtue, rarity, is_secret: false, friend_name: null })

/** Deterministic stand-in so order assertions are not flaky. */
const noShuffle = <T,>(items: T[]) => [...items]

describe('planElimination', () => {
  const contents = [
    content('NURTURING', 'POUCH'),
    content('SERENITY', 'SAFE'),
    content('FREEDOM', 'SANCTUM'),
    content('VITALITY', 'VAULT'),
  ]

  it('crowns whatever the server actually dropped', () => {
    const plan = planElimination(contents, { virtue: 'FREEDOM', rarity: 'SANCTUM' }, noShuffle)
    expect(plan?.winner).toBe(2)
  })

  it('eliminates every other content, exactly once each', () => {
    const plan = planElimination(contents, { virtue: 'SERENITY', rarity: 'SAFE' }, noShuffle)

    expect(plan?.order).toHaveLength(contents.length - 1)
    expect(new Set(plan?.order).size).toBe(contents.length - 1)
    expect(plan?.order).not.toContain(plan?.winner)
  })

  it('never eliminates the winner however the losers are shuffled', () => {
    // The shuffle is theatre; it must not be able to touch the outcome.
    for (let run = 0; run < 50; run += 1) {
      const plan = planElimination(contents, { virtue: 'VITALITY', rarity: 'VAULT' })
      expect(plan?.winner).toBe(3)
      expect(plan?.order).not.toContain(3)
      expect(plan?.order).toHaveLength(3)
    }
  })

  it('matches on virtue and rarity together, not either alone', () => {
    const tricky = [
      content('SERENITY', 'POUCH'),
      content('NURTURING', 'SAFE'),
      content('SERENITY', 'SAFE'),
    ]
    const plan = planElimination(tricky, { virtue: 'SERENITY', rarity: 'SAFE' }, noShuffle)
    expect(plan?.winner).toBe(2)
  })

  it('picks one when a treasure holds duplicates', () => {
    // Two identical contents are indistinguishable to the player, so either
    // is a truthful representation of the win.
    const dupes = [content('SERENITY', 'SAFE'), content('SERENITY', 'SAFE')]
    const plan = planElimination(dupes, { virtue: 'SERENITY', rarity: 'SAFE' }, noShuffle)

    expect(plan?.winner).toBe(0)
    expect(plan?.order).toEqual([1])
  })

  it('skips the theatre when nothing on screen matches the drop', () => {
    // Contents moved under us. Darkening everything and crowning the wrong
    // one would be worse than showing no animation.
    const plan = planElimination(contents, { virtue: 'PRESENCE', rarity: 'CHEST' }, noShuffle)
    expect(plan).toBeNull()
  })

  it('matches the rarity the content was won at, not the relabelled one', () => {
    // Buying triggers the 27:9:3:1 recalculation, so the receptacle that comes
    // back may carry a different rarity than the treasure displayed. Callers
    // must pass dropped_rarity; this pins what happens if they pass the
    // post-recalculation one instead -- no match, and no wrong crown.
    const asWon = planElimination(contents, { virtue: 'SERENITY', rarity: 'SAFE' }, noShuffle)
    expect(asWon?.winner).toBe(1)

    const relabelled = planElimination(
      contents,
      { virtue: 'SERENITY', rarity: 'SACK' },
      noShuffle,
    )
    expect(relabelled).toBeNull()
  })

  it('handles a treasure down to its last content', () => {
    const one = [content('SERENITY', 'SAFE')]
    const plan = planElimination(one, { virtue: 'SERENITY', rarity: 'SAFE' }, noShuffle)

    expect(plan?.winner).toBe(0)
    expect(plan?.order).toEqual([])
  })
})
