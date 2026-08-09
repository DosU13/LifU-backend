import { RECEPTACLE_RARITIES } from '../types'
import type { Receptacle, TreasureContentPreview } from '../types'

/**
 * Plans the buy animation: which content survives, and the order the rest go out.
 *
 * The survivor is decided by the server — it is whichever receptacle the buy
 * actually dropped. This only picks the *order the losers fade*, which is pure
 * theatre and safe to arrange however reads best. If the client chose the
 * winner, the animation would eventually disagree with the receptacle the
 * player was really given.
 *
 * The losers go out worst-first, so whatever is left standing at the end is
 * the best of what was in the treasure and the tension climbs to the final
 * beat instead of leaking away when the Sanctum goes out third. This tells the
 * player nothing: every content is on screen and labelled from the moment the
 * treasure is selected. Ties are shuffled, so equal rarities do not fall in a
 * fixed order every time.
 *
 * Contents deliberately expose no id (they omit value and reward text so a
 * treasure cannot be scouted), so the drop is matched on virtue and rarity.
 * Duplicates are possible — two Chests of Serenity in one treasure — and any
 * one of them is an equally true representation of what was won.
 */

export interface EliminationPlan {
  winner: number
  /** Indices to darken, in the order they should go out. */
  order: number[]
}

type Shuffle = <T>(items: T[]) => T[]

const shuffleInPlace: Shuffle = (items) => {
  const out = [...items]
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j] as never, out[i] as never]
  }
  return out
}

export function planElimination(
  contents: TreasureContentPreview[],
  drop: Pick<Receptacle, 'virtue' | 'rarity'>,
  shuffle: Shuffle = shuffleInPlace,
): EliminationPlan | null {
  const winner = contents.findIndex(
    (c) => c.virtue === drop.virtue && c.rarity === drop.rarity,
  )

  // Nothing on screen matches what the server handed over — the contents must
  // have moved under us. Better to skip the theatre than to darken everything
  // and crown the wrong one.
  if (winner === -1) return null

  const losers = contents
    .map((content, index) => ({ index, rank: RECEPTACLE_RARITIES.indexOf(content.rarity) }))
    .filter((entry) => entry.index !== winner)

  // Shuffle first, then sort. Array.prototype.sort is stable, so the shuffle
  // survives as the tie-break within each rarity while the ranking decides
  // the overall order.
  const order = [...shuffle(losers)].sort((a, b) => a.rank - b.rank)

  return { winner, order: order.map((entry) => entry.index) }
}
