import { useState } from 'react'

import { useGameStore } from '../state/store'
import type { FriendLink } from '../types'

type Mode = 'mine' | 'secret'

interface Props {
  friends: FriendLink[]
  /** Called after a successful seal, so the list above can pick it up. */
  onSealed: () => void
}

/**
 * Where a reward goes in. What it became is never shown back here — see
 * ARCHITECTURE §2: the response to a seal carries no virtue, rarity or id.
 */
export function RewardComposer({ friends, onSealed }: Props) {
  const [mode, setMode] = useState<Mode>('mine')
  const [text, setText] = useState('')
  const [friendName, setFriendName] = useState('')
  const [busy, setBusy] = useState(false)
  const submitReward = useGameStore((s) => s.submitReward)

  const isSecret = mode === 'secret'
  const canSubmit = text.trim().length > 0 && !busy && (!isSecret || friendName !== '')

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    const ok = await submitReward(text.trim(), isSecret, isSecret ? friendName : undefined)
    setBusy(false)
    if (ok) {
      setText('')
      onSealed()
    }
  }

  function switchMode(next: Mode) {
    setMode(next)
    // Never carry text across modes — a pasted secret must not end up visible
    // in the "for me" field a moment later.
    setText('')
  }

  return (
    <div className="composer">
      <div className="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'mine'}
          className={mode === 'mine' ? 'tab active' : 'tab'}
          onClick={() => switchMode('mine')}
        >
          For me
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'secret'}
          className={mode === 'secret' ? 'tab active' : 'tab'}
          onClick={() => switchMode('secret')}
        >
          Secret gift
        </button>
      </div>

      {isSecret && (
        <div className="composer-field">
          <span>From</span>
          <select
            value={friendName}
            onChange={(event) => setFriendName(event.target.value)}
            aria-label="Friend"
          >
            <option value="">Choose a friend…</option>
            {friends.map((friend) => (
              <option key={friend.name} value={friend.name}>
                {friend.name}
              </option>
            ))}
          </select>
          {friends.length === 0 && <span>Create a friend link below first.</span>}
        </div>
      )}

      <form onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          className={isSecret ? 'masked' : undefined}
          placeholder={
            isSecret
              ? 'Paste it here — you will not see it, on this screen or anywhere else'
              : 'A reward worth working toward…'
          }
          aria-label={isSecret ? 'Secret gift text (hidden)' : 'A reward worth working toward'}
        />
        <div className="composer-foot">
          <span className="hint">
            {isSecret
              ? "Stays hidden until the receptacle it's sealed into is opened."
              : 'Sealed away — which receptacle it becomes is not shown, even to you.'}
          </span>
          <button type="submit" className="btn-primary" disabled={!canSubmit}>
            {busy ? 'Sealing…' : 'Seal it'}
          </button>
        </div>
      </form>
    </div>
  )
}
