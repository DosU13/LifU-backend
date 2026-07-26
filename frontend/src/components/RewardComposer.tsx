import { useState } from 'react'

import type { FriendLink } from '../types'
import { useGameStore } from '../state/store'

type Mode = 'mine' | 'secret'

interface Props {
  friends: FriendLink[]
}

export function RewardComposer({ friends }: Props) {
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
    if (ok) setText('')
  }

  function switchMode(next: Mode) {
    setMode(next)
    setText('') // never carry text across modes — it could expose a pasted secret
  }

  return (
    <section className="panel">
      <h2>Hide a reward</h2>

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

      {isSecret ? (
        <p className="muted small">
          Paste a friend&apos;s message without reading it — the text stays hidden here and in the
          app until you actually open the receptacle. Secret gifts are always worth more than 50.
        </p>
      ) : (
        <p className="muted small">
          Something you would like to find later. It gets sealed into a receptacle whose rarity
          depends on how it compares to your other rewards.
        </p>
      )}

      <form onSubmit={onSubmit}>
        {isSecret && (
          <label className="field">
            <span className="muted small">From</span>
            <select
              value={friendName}
              onChange={(e) => setFriendName(e.target.value)}
              aria-label="Friend"
            >
              <option value="">Choose a friend…</option>
              {friends.map((friend) => (
                <option key={friend.name} value={friend.name}>
                  {friend.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          className={isSecret ? 'masked' : undefined}
          placeholder={
            isSecret ? 'Paste it here — you will not see it' : 'Lunch at my favourite place'
          }
          aria-label={isSecret ? 'Secret gift text (hidden)' : 'Reward description'}
        />

        {isSecret && friends.length === 0 && (
          <p className="muted small">Create a friend link first so the gift can be attributed.</p>
        )}

        <button type="submit" disabled={!canSubmit}>
          {busy ? 'Sealing…' : 'Seal it away'}
        </button>
      </form>
    </section>
  )
}
