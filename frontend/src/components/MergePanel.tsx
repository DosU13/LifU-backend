import { useState } from 'react'

import { COMBINED_PAIRS, elementLabel, label, nextRarity, sellPrice } from '../domain'
import { useGameStore } from '../state/store'
import {
  BASE_ELEMENTS,
  COLLECTABLE_RARITIES,
  ELEMENTS,
  stockKey,
  type CollectableRarity,
  type Element,
} from '../types'

const MERGE_COST = 3

export function MergePanel() {
  const stocks = useGameStore((s) => s.stocks)
  const mergeUp = useGameStore((s) => s.mergeUp)
  const mergeHarmony = useGameStore((s) => s.mergeHarmony)
  const combine = useGameStore((s) => s.combine)
  const sell = useGameStore((s) => s.sell)

  const [busy, setBusy] = useState(false)
  const [pairIndex, setPairIndex] = useState(0)
  const [combineRarity, setCombineRarity] = useState<CollectableRarity>('FRAGMENT')
  const [harmonyRarity, setHarmonyRarity] = useState<CollectableRarity>('FRAGMENT')

  const held = (element: Element, rarity: CollectableRarity) => stocks[stockKey(element, rarity)] ?? 0

  async function run(action: () => Promise<boolean>) {
    setBusy(true)
    await action()
    setBusy(false)
  }

  const ownedElements = ELEMENTS.filter((element) =>
    COLLECTABLE_RARITIES.some((rarity) => held(element, rarity) > 0),
  )

  const harmonyReady = BASE_ELEMENTS.every((element) => held(element, harmonyRarity) > 0)
  const pair = COMBINED_PAIRS[pairIndex] ?? COMBINED_PAIRS[0]!
  const combineReady =
    held(pair.a, combineRarity) > 0 &&
    held(pair.b, combineRarity) > 0 &&
    held('HARMONY', combineRarity) > 0

  return (
    <section className="panel">
      <h2>Collectables</h2>

      {ownedElements.length === 0 ? (
        <p className="muted small">Nothing yet — log a task to earn your first fragments.</p>
      ) : (
        <table className="inventory">
          <thead>
            <tr>
              <th scope="col">Element</th>
              {COLLECTABLE_RARITIES.map((rarity) => (
                <th key={rarity} scope="col">
                  {label(rarity)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ownedElements.map((element) => (
              <tr key={element}>
                <th scope="row">{elementLabel(element)}</th>
                {COLLECTABLE_RARITIES.map((rarity) => {
                  const count = held(element, rarity)
                  const upgrade = nextRarity(rarity)
                  return (
                    <td key={rarity}>
                      <span className={count > 0 ? 'count' : 'count zero'}>{count}</span>
                      {upgrade && (
                        <button
                          type="button"
                          className="mini"
                          disabled={busy || count < MERGE_COST}
                          title={`Merge 3 into 1 ${label(upgrade)}`}
                          onClick={() => void run(() => mergeUp(element, rarity))}
                        >
                          ↑
                        </button>
                      )}
                      {count > 0 && (
                        <button
                          type="button"
                          className="mini sell"
                          disabled={busy}
                          title={`Sell 1 for ${sellPrice(element, rarity)} coins`}
                          onClick={() => void run(() => sell(element, rarity, 1))}
                        >
                          ◈
                        </button>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Harmony merge</h3>
      <p className="muted small">
        One of each base element becomes five harmony — then the build-up rolls for extras.
      </p>
      <div className="row">
        <select
          value={harmonyRarity}
          onChange={(e) => setHarmonyRarity(e.target.value as CollectableRarity)}
          aria-label="Harmony rarity"
        >
          {COLLECTABLE_RARITIES.map((rarity) => (
            <option key={rarity} value={rarity}>
              {label(rarity)}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || !harmonyReady}
          onClick={() => void run(() => mergeHarmony(harmonyRarity))}
        >
          Merge to harmony
        </button>
      </div>
      {!harmonyReady && (
        <p className="muted small">
          Needs one of each: {BASE_ELEMENTS.map((e) => label(e)).join(', ')}.
        </p>
      )}

      <h3>Combine</h3>
      <p className="muted small">
        Two base elements plus one harmony, all the same rarity, become a combined element — the
        keys that open receptacles.
      </p>
      <div className="row">
        <select
          value={pairIndex}
          onChange={(e) => setPairIndex(Number(e.target.value))}
          aria-label="Element pair"
        >
          {COMBINED_PAIRS.map((option, index) => (
            <option key={option.result} value={index}>
              {label(option.a)} + {label(option.b)} → {label(option.result)}
            </option>
          ))}
        </select>
        <select
          value={combineRarity}
          onChange={(e) => setCombineRarity(e.target.value as CollectableRarity)}
          aria-label="Combine rarity"
        >
          {COLLECTABLE_RARITIES.map((rarity) => (
            <option key={rarity} value={rarity}>
              {label(rarity)}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || !combineReady}
          onClick={() => void run(() => combine(pair.a, pair.b, combineRarity))}
        >
          Combine
        </button>
      </div>
      {!combineReady && (
        <p className="muted small">
          Needs 1 {label(pair.a)}, 1 {label(pair.b)} and 1 Harmony at {label(combineRarity)}.
        </p>
      )}
    </section>
  )
}
