import { COMBINED_PAIRS, isBaseElement, keyForReceptacle, label, nextRarity } from '../domain'
import { stockKey } from '../types'
import type { CollectableRarity, Element, Receptacle, Stocks } from '../types'

/**
 * One bench, four operations.
 *
 * The player drops things in and the button names whatever those things
 * actually make. That is nicer than three separate panels, but it means this
 * function has to mirror the backend's merge rules exactly — see
 * services/merger_service.py and ARCHITECTURE §7.2/§7.3. When it cannot make
 * anything it says why, because a silently disabled button is infuriating.
 *
 * Deliberately pure and component-free so every rule can be table-tested.
 */

export type BenchItem =
  | { type: 'collectable'; element: Element; rarity: CollectableRarity }
  | { type: 'receptacle'; receptacle: Receptacle }

export type BenchOp =
  | {
      kind: 'merge'
      label: string
      element: Element
      rarity: CollectableRarity
      /** The rarity this produces — the caller needs it too, to animate the result. */
      to: CollectableRarity
    }
  | { kind: 'harmony'; label: string; rarity: CollectableRarity }
  | {
      kind: 'combine'
      label: string
      a: Element
      b: Element
      rarity: CollectableRarity
      /** The combined element this produces. */
      result: Element
    }
  | { kind: 'open'; label: string; receptacle: Receptacle }
  | { kind: 'blocked'; label: string; reason: string }

const MERGE_COUNT = 3
const BASE_ELEMENT_COUNT = 5

function blocked(reason: string, buttonLabel = 'Nothing to make'): BenchOp {
  return { kind: 'blocked', label: buttonLabel, reason }
}

export function detectOp(items: BenchItem[], stocks: Stocks): BenchOp {
  if (items.length === 0) {
    return blocked('Drag items in to merge, combine, or open.', 'Merge')
  }

  const receptacles = items.filter((i) => i.type === 'receptacle')

  if (receptacles.length > 0) {
    if (items.length > 1) {
      return blocked('A receptacle opens on its own — take everything else out.')
    }
    const { receptacle } = receptacles[0] as Extract<BenchItem, { type: 'receptacle' }>
    const key = keyForReceptacle(receptacle.virtue, receptacle.rarity)
    const held = stocks[stockKey(key.element, key.rarity)] ?? 0

    if (held < 1) {
      return blocked(
        `Needs one ${label(key.element)} ${label(key.rarity)} — you have none.`,
        'No key',
      )
    }
    return {
      kind: 'open',
      label: 'Open it',
      receptacle,
    }
  }

  const collectables = items as Extract<BenchItem, { type: 'collectable' }>[]
  const rarities = new Set(collectables.map((c) => c.rarity))
  if (rarities.size > 1) {
    return blocked('Everything on the bench has to be the same rarity.')
  }

  const rarity = collectables[0]!.rarity
  const elements = collectables.map((c) => c.element)
  const distinct = new Set(elements)

  // --- merge up: three of exactly the same thing ---
  if (distinct.size === 1) {
    const element = elements[0]!
    if (collectables.length !== MERGE_COUNT) {
      return blocked(
        `Merging up takes three of the same — you have ${collectables.length}.`,
      )
    }
    const next = nextRarity(rarity)
    if (next === null) {
      return blocked('A Core is already the highest rarity there is.', 'Already a Core')
    }
    return {
      kind: 'merge',
      label: `Merge up → ${label(element)} ${label(next)}`,
      element,
      rarity,
      to: next,
    }
  }

  // --- harmony: one of each of the five base elements ---
  if (distinct.size === BASE_ELEMENT_COUNT && elements.every(isBaseElement)) {
    if (collectables.length !== BASE_ELEMENT_COUNT) {
      return blocked('A harmony merge takes exactly one of each base element.')
    }
    return { kind: 'harmony', label: 'Harmony merge', rarity }
  }

  // --- combine: two base elements plus a harmony ---
  const harmonies = elements.filter((e) => e === 'HARMONY')
  if (harmonies.length === 1 && collectables.length === 3) {
    const bases = elements.filter((e) => e !== 'HARMONY')
    if (!bases.every(isBaseElement)) {
      return blocked('Only base elements combine — the other two must be base.')
    }
    if (new Set(bases).size !== 2) {
      return blocked('Combining takes two different base elements.')
    }
    const [a, b] = bases as [Element, Element]
    const pair = COMBINED_PAIRS.find(
      (p) => (p.a === a && p.b === b) || (p.a === b && p.b === a),
    )
    if (!pair) {
      return blocked(`${label(a)} and ${label(b)} do not combine.`)
    }
    return {
      kind: 'combine',
      label: `Combine → ${label(pair.result)}`,
      a,
      b,
      rarity,
      result: pair.result,
    }
  }

  if (harmonies.length > 1) {
    return blocked('Combining uses a single Harmony.')
  }
  if (elements.some((e) => !isBaseElement(e) && e !== 'HARMONY')) {
    return blocked('Combined elements cannot be merged further, only merged up.')
  }

  return blocked(
    'Three of a kind to merge up, five different base elements for harmony, ' +
      'or two base plus a Harmony to combine.',
  )
}

/**
 * How many times an operation could run given what is actually in stock.
 * The quantity field is clamped to this so a bench cannot promise a merge
 * the hoard cannot pay for.
 */
export function maxRepeats(op: BenchOp, stocks: Stocks): number {
  const held = (element: Element, rarity: CollectableRarity) =>
    stocks[stockKey(element, rarity)] ?? 0

  switch (op.kind) {
    case 'merge':
      return Math.floor(held(op.element, op.rarity) / MERGE_COUNT)
    case 'harmony': {
      const bases: Element[] = ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH']
      return Math.min(...bases.map((e) => held(e, op.rarity)))
    }
    case 'combine':
      return Math.min(
        held(op.a, op.rarity),
        held(op.b, op.rarity),
        held('HARMONY', op.rarity),
      )
    case 'open':
      return 1
    default:
      return 0
  }
}
