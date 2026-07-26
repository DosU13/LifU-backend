import { useState } from 'react'

import { label } from '../domain'
import { useGameStore } from '../state/store'
import type { Treasure } from '../types'

// Mirrors core/constants.py PITY_THRESHOLDS.
const PITY_THRESHOLD = { VAULT: 27, SANCTUM: 81 } as const

function PityBar({ rarity, count }: { rarity: keyof typeof PITY_THRESHOLD; count: number }) {
  const threshold = PITY_THRESHOLD[rarity]
  const ready = count >= threshold
  return (
    <li>
      <span className="bar-label">{label(rarity)}</span>
      <span className="bar-track">
        <span
          className={ready ? 'bar-fill ready' : 'bar-fill'}
          style={{ width: `${Math.min((count / threshold) * 100, 100)}%` }}
        />
      </span>
      <span className="bar-value">
        {count}/{threshold}
      </span>
    </li>
  )
}

export function TreasurePanel() {
  const treasures = useGameStore((s) => s.treasures)
  const selectedId = useGameStore((s) => s.selectedTreasureId)
  const selectTreasure = useGameStore((s) => s.selectTreasure)
  const coins = useGameStore((s) => s.coins)
  const buyTreasure = useGameStore((s) => s.buyTreasure)
  const discardTreasure = useGameStore((s) => s.discardTreasure)
  const [busy, setBusy] = useState(false)

  const selected: Treasure | undefined =
    treasures.find((t) => t.id === selectedId) ?? treasures[0]

  if (!selected) {
    return (
      <section className="panel">
        <h2>Treasures</h2>
        <p className="muted small">
          No treasures yet — hide a reward and one will be built around it.
        </p>
      </section>
    )
  }

  const affordable = coins >= selected.price

  async function run(action: () => Promise<boolean>) {
    setBusy(true)
    await action()
    setBusy(false)
  }

  return (
    <section className="panel">
      <h2>Treasures</h2>

      <div className="tabs" role="tablist">
        {treasures.map((treasure) => (
          <button
            key={treasure.id}
            type="button"
            role="tab"
            aria-selected={treasure.id === selected.id}
            className={treasure.id === selected.id ? 'tab active' : 'tab'}
            onClick={() => selectTreasure(treasure.id)}
          >
            Slot {treasure.slot}
          </button>
        ))}
      </div>

      <p className="muted small">
        Costs <strong>◈ {selected.price}</strong> per try · {selected.contents.length} still
        inside. The price was fixed when the treasure was built, so it never gets cheaper.
      </p>

      {selected.contents.length > 0 && (
        <ul className="chips">
          {selected.contents.map((item, index) => (
            <li key={`${item.virtue}-${index}`}>
              {label(item.rarity)} of {label(item.virtue)}
              {item.is_secret && <span title={`Secret from ${item.friend_name}`}> ·  secret</span>}
            </li>
          ))}
        </ul>
      )}

      <h3>Pity</h3>
      <ul className="bars">
        <PityBar rarity="VAULT" count={selected.pity.VAULT ?? 0} />
        <PityBar rarity="SANCTUM" count={selected.pity.SANCTUM ?? 0} />
      </ul>
      <p className="muted small">
        These counters belong to this treasure. Let it go and they start again from zero.
      </p>

      <div className="row">
        <button
          type="button"
          disabled={busy || !affordable}
          onClick={() => void run(() => buyTreasure(selected.id))}
        >
          {affordable ? `Try it — ◈ ${selected.price}` : `Need ◈ ${selected.price}`}
        </button>
        <button
          type="button"
          className="tab"
          disabled={busy}
          onClick={() => void run(() => discardTreasure(selected.id))}
          title="Once a day, across all slots"
        >
          Let it go
        </button>
      </div>
    </section>
  )
}
