import { useState } from 'react'

import { useSessionStore } from '../state/session'
import '../ui/gate.css'

export function LoginGate() {
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const login = useSessionStore((s) => s.login)
  const error = useSessionStore((s) => s.error)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    await login(password)
    setBusy(false)
    setPassword('')
  }

  return (
    <main className="gate panel">
      <h1>LifU</h1>
      <p className="muted">Sign in to play.</p>
      <form onSubmit={onSubmit}>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          aria-label="Password"
        />
        <button type="submit" className="btn-primary" disabled={busy || password.length === 0}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </main>
  )
}
