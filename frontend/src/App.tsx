import { useEffect, useState } from 'react'

import { EventToasts } from './components/EventToasts'
import { FriendGate } from './components/FriendGate'
import { LoginGate } from './components/LoginGate'
import { Admin } from './layouts/Admin'
import { Ledger } from './layouts/Ledger'
import { Treasury } from './layouts/Treasury'
import { Vault } from './layouts/Vault'
import { routeFromPath } from './routing'
import { useSessionStore } from './state/session'
import { useGameStore } from './state/store'
import { Deck } from './ui/Deck'
import { TopBar } from './ui/TopBar'

/**
 * The root page. Three full-height layouts the deck snaps between.
 *
 * The sections currently hold the Part-I panels so the game stays fully
 * playable while Part II is built out; phases 18-20 replace their contents
 * one layout at a time, and Phase 23 deletes what is left over.
 */
function GameShell() {
  const { hydrate, hydrated, loading, error } = useGameStore()

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  if (error) {
    return (
      <div className="centered-page">
        <p role="alert" className="error">{error}</p>
      </div>
    )
  }

  if (!hydrated) {
    return (
      <div className="centered-page">
        <p className="muted">{loading ? 'Loading your world…' : ''}</p>
      </div>
    )
  }

  return (
    <>
      <TopBar />
      <EventToasts />
      <Deck
        sections={[
          { id: 'ledger', label: 'Log what you did', node: <Ledger /> },
          { id: 'vault', label: 'Everything you own', node: <Vault /> },
          { id: 'treasury', label: 'Treasures', node: <Treasury /> },
        ]}
      />
    </>
  )
}

export function App() {
  const { authenticated, checking, check } = useSessionStore()
  const [route] = useState(routeFromPath)

  useEffect(() => {
    // A friend link never carries the owner's session; it starts at the gate.
    if (route.kind !== 'friend') void check()
  }, [check, route.kind])

  if (route.kind === 'friend' && !authenticated) {
    return <FriendGate friendName={route.name} />
  }

  if (!authenticated) {
    if (checking) return <p className="muted centered">…</p>
    return <LoginGate />
  }

  return route.kind === 'admin' ? <Admin /> : <GameShell />
}
