import { useEffect } from 'react'

import { LoginGate } from './components/LoginGate'
import { StateDebugView } from './components/StateDebugView'
import { WalletBadge } from './components/WalletBadge'
import { useSessionStore } from './state/session'
import { useGameStore } from './state/store'

function GameShell() {
  const isTrial = useSessionStore((s) => s.isTrial)
  const logout = useSessionStore((s) => s.logout)
  const { hydrate, reset, hydrated, loading, error } = useGameStore()

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  async function onSignOut() {
    await logout()
    reset()
  }

  return (
    <div className="shell">
      <header>
        <h1>LifU</h1>
        <div className="header-right">
          {isTrial && <span className="trial-badge">Trial — nothing is saved</span>}
          <WalletBadge />
          <button type="button" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </header>

      {error && <p role="alert" className="error">{error}</p>}
      {loading && !hydrated && <p className="muted">Loading your world…</p>}
      {hydrated && <StateDebugView />}
    </div>
  )
}

export function App() {
  const { authenticated, checking, check } = useSessionStore()

  useEffect(() => {
    void check()
  }, [check])

  if (checking) return <p className="muted centered">…</p>
  return authenticated ? <GameShell /> : <LoginGate />
}
