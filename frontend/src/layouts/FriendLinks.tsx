import { useState } from 'react'

import { ApiError } from '../api'
import type { FriendLink } from '../types'

interface Props {
  friends: FriendLink[]
  onCreate: (name: string) => Promise<FriendLink>
}

export function FriendLinks({ friends, onCreate }: Props) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (trimmed.length === 0) return
    setBusy(true)
    setError(null)
    try {
      await onCreate(trimmed)
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
    <div className="friend-links">
      <div className="label">Friend links</div>
      <p className="hint friend-hint">
        Each friend gets their own link and a sandbox to try the game in. Nothing they do
        touches your save.
      </p>

      <form className="friend-form" onSubmit={onSubmit}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="friend name"
          aria-label="Friend name"
        />
        <button type="submit" className="btn-ghost" disabled={busy || name.trim().length === 0}>
          Create link
        </button>
      </form>

      {error && (
        <p role="alert" className="friend-error">
          {error}
        </p>
      )}

      {friends.length > 0 && (
        <ul className="friend-list">
          {friends.map((friend) => (
            <li key={friend.name}>
              <code>{friend.url}</code>
              <button type="button" className="btn-ghost mini" onClick={() => void copy(friend.url)}>
                {copied === friend.url ? 'copied' : 'copy'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
