import { useGameStore } from '../state/store'

/**
 * Temporary window onto the raw world while the real UI is built in later
 * phases. Non-zero stocks only, so 96 counters do not drown the view.
 */
export function StateDebugView() {
  const { coins, stocks, treasures, droppedReceptacles, stats } = useGameStore()

  const heldStocks = Object.entries(stocks)
    .filter(([, count]) => count > 0)
    .sort(([a], [b]) => a.localeCompare(b))

  return (
    <section className="debug">
      <h2>World</h2>

      <h3>Collectables ({heldStocks.length} held)</h3>
      {heldStocks.length === 0 ? (
        <p className="muted">Nothing yet — complete a task to earn fragments.</p>
      ) : (
        <ul className="chips">
          {heldStocks.map(([key, count]) => (
            <li key={key}>
              {key.replace('_', ' ')} <strong>×{count}</strong>
            </li>
          ))}
        </ul>
      )}

      <h3>Treasures ({treasures.length})</h3>
      {treasures.length === 0 ? (
        <p className="muted">No treasures — add rewards to fill the pool.</p>
      ) : (
        <ul>
          {treasures.map((treasure) => (
            <li key={treasure.id}>
              Slot {treasure.slot} · price {treasure.price} · {treasure.contents.length} inside ·
              pity V{treasure.pity.VAULT ?? 0}/S{treasure.pity.SANCTUM ?? 0}
            </li>
          ))}
        </ul>
      )}

      <h3>Waiting to open ({droppedReceptacles.length})</h3>
      {droppedReceptacles.length === 0 ? (
        <p className="muted">Nothing dropped yet.</p>
      ) : (
        <ul>
          {droppedReceptacles.map((receptacle) => (
            <li key={receptacle.id}>
              {receptacle.rarity} of {receptacle.virtue} — needs{' '}
              <strong>
                {receptacle.key_needed.element} {receptacle.key_needed.rarity}
              </strong>
            </li>
          ))}
        </ul>
      )}

      <h3>Stats</h3>
      <p className="muted">
        Streak {stats?.streak ?? 0} day(s) · {Object.keys(stats?.per_day ?? {}).length} active day(s)
      </p>

      <details>
        <summary>Raw state</summary>
        <pre>
          {JSON.stringify({ coins, stocks, treasures, droppedReceptacles, stats }, null, 2)}
        </pre>
      </details>
    </section>
  )
}
