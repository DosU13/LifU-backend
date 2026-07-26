import { useCallback, useEffect, useState } from 'react'

import { api } from './api'
import { EventToasts } from './components/EventToasts'
import { FriendLinksPanel } from './components/FriendLinksPanel'
import { LoginGate } from './components/LoginGate'
import { MergePanel } from './components/MergePanel'
import { RewardComposer } from './components/RewardComposer'
import { StateDebugView } from './components/StateDebugView'
import { StatsPanel } from './components/StatsPanel'
import { TaskComposer } from './components/TaskComposer'
import { TreasurePanel } from './components/TreasurePanel'
import { VaultPanel } from './components/VaultPanel'
import { WalletBadge } from './components/WalletBadge'
import { SceneCanvas } from './scene/SceneCanvas'
import { useSessionStore } from './state/session'
import { useGameStore } from './state/store'
import type { FriendLink } from './types'

function GameShell() {
  const isTrial = useSessionStore((s) => s.isTrial)
  const logout = useSessionStore((s) => s.logout)
  const { hydrate, reset, hydrated, loading, error } = useGameStore()
  const [friends, setFriends] = useState<FriendLink[]>([])

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  useEffect(() => {
    // Friend links are owner-only; a trial simply has none to manage.
    if (isTrial) return
    void api
      .listFriends()
      .then(({ friends: list }) => setFriends(list))
      .catch(() => setFriends([]))
  }, [isTrial])

  const createFriend = useCallback(async (name: string) => {
    const link = await api.createFriend(name)
    setFriends((current) => [...current, link])
    return link
  }, [])

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

      <EventToasts />

      {error && <p role="alert" className="error">{error}</p>}
      {loading && !hydrated && <p className="muted">Loading your world…</p>}

      {hydrated && (
        <>
          <SceneCanvas />
          <div className="grid">
            <TreasurePanel />
            <VaultPanel />
            <TaskComposer />
            <RewardComposer friends={friends} />
            <MergePanel />
            <StatsPanel />
            {!isTrial && <FriendLinksPanel friends={friends} onCreate={createFriend} />}
            <StateDebugView />
          </div>
        </>
      )}
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
