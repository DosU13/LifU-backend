import { useCallback, useEffect, useState } from 'react'

import { api } from '../api'
import { EventToasts } from '../components/EventToasts'
import { TopBar } from '../ui/TopBar'
import { FriendLinks } from './FriendLinks'
import { RewardComposer } from './RewardComposer'
import { RewardList } from './RewardList'
import type { FriendLink, Reward } from '../types'

import '../ui/composer.css'
import './admin.css'

/**
 * Rewards management. A separate page, not a fourth layout — logging what
 * you want to work toward is a different mode from playing the game.
 */
export function Admin() {
  const [friends, setFriends] = useState<FriendLink[]>([])
  const [rewards, setRewards] = useState<Reward[]>([])
  const [loadingRewards, setLoadingRewards] = useState(true)

  const loadRewards = useCallback(() => {
    return api
      .listRewards()
      .then(({ rewards: list }) => setRewards(list))
      .catch(() => setRewards([]))
  }, [])

  useEffect(() => {
    void api
      .listFriends()
      .then(({ friends: list }) => setFriends(list))
      .catch(() => setFriends([]))
    void loadRewards().finally(() => setLoadingRewards(false))
  }, [loadRewards])

  const createFriend = useCallback(async (name: string) => {
    const link = await api.createFriend(name)
    setFriends((current) => [...current, link])
    return link
  }, [])

  return (
    <>
      <TopBar showAdminLink={false} />
      <EventToasts />
      <div className="admin">
        <a className="pill back-link" href="/">
          ← Back to the game
        </a>

        <h1>Rewards</h1>
        <p className="hint admin-sub">
          Things worth wanting. Each gets sealed into a receptacle you will have to earn the
          key for.
        </p>

        <RewardComposer friends={friends} onSealed={() => void loadRewards()} />

        <RewardList rewards={rewards} loading={loadingRewards} />

        <p className="sealed-note">
          <b>You cannot see which receptacle holds what.</b> Rarity is recalculated across
          everything you own each time this list changes, so showing it here would tell you
          exactly which reward is the best one — and that is the whole surprise. You will find
          out when you open it.
        </p>

        <FriendLinks friends={friends} onCreate={createFriend} />
      </div>
    </>
  )
}
