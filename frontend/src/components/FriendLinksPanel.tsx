import { useState } from 'react'

import { ApiError } from '../api'
import type { FriendLink } from '../types'

interface Props {
  friends: FriendLink[]
  onCreate: (name: string) => Promise<FriendLink>
}

export function FriendLinksPanel({ friends, onCreate }: Props) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (name.trim().length === 0) return
    setBusy(true)
    setError(null)
    try {
      await onCreate(name.trim())
      setName('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create that link.')
    } finally {
      setBusy(false)
    }
  }

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(url)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      setError('Could not copy — select the link and copy it manually.')
    }
  }

  return (
    <section className="panel">
      <h2>Friend links</h2>
      <p className="muted small">
        Each friend gets their own link. It opens a sandbox — they can try the game, but nothing
        they do touches yours.
      </p>

      <form onSubmit={onSubmit} className="row">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="friend name"
          aria-label="Friend name"
        />
        <button type="submit" disabled={busy || name.trim().length === 0}>
          Create link
        </button>
      </form>
      {error && <p role="alert" className="error small">{error}</p>}

      {friends.length > 0 && (
        <ul className="links">
          {friends.map((friend) => (
            <li key={friend.name}>
              <code>{friend.url}</code>
              <button type="button" className="mini" onClick={() => void copy(friend.url)}>
                {copied === friend.url ? 'copied' : 'copy'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
