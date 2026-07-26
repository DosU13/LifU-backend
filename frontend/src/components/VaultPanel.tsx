import { useState } from 'react'

import { elementLabel, label } from '../domain'
import { useGameStore } from '../state/store'
import { stockKey, type Receptacle } from '../types'

function ReceptacleRow({ receptacle }: { receptacle: Receptacle }) {
  const stocks = useGameStore((s) => s.stocks)
  const openReceptacle = useGameStore((s) => s.openReceptacle)
  const [busy, setBusy] = useState(false)

  const { element, rarity } = receptacle.key_needed
  const heldKeys = stocks[stockKey(element, rarity)] ?? 0
  const canOpen = heldKeys > 0

  async function onOpen() {
    setBusy(true)
    await openReceptacle(receptacle.id)
    setBusy(false)
  }

  return (
    <li className="vault-row">
      <div>
        <strong>
          {label(receptacle.rarity)} of {label(receptacle.virtue)}
        </strong>
        {receptacle.is_secret && (
          <span className="muted small"> · secret from {receptacle.friend_name}</span>
        )}
        <div className="muted small">
          Needs {elementLabel(element)} {label(rarity)} —{' '}
          {canOpen ? `you have ${heldKeys}` : 'you have none'}
        </div>
      </div>
      <button type="button" disabled={busy || !canOpen} onClick={() => void onOpen()}>
        {busy ? 'Opening…' : 'Open'}
      </button>
    </li>
  )
}

export function VaultPanel() {
  const dropped = useGameStore((s) => s.droppedReceptacles)

  return (
    <section className="panel">
      <h2>Waiting to open</h2>
      {dropped.length === 0 ? (
        <p className="muted small">
          Nothing yet. Try a treasure — whatever drops lands here until you craft its key.
        </p>
      ) : (
        <ul className="vault">
          {dropped.map((receptacle) => (
            <ReceptacleRow key={receptacle.id} receptacle={receptacle} />
          ))}
        </ul>
      )}
    </section>
  )
}
