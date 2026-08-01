import { relativeTime } from '../ui/relativeTime'
import type { Reward } from '../types'

interface Props {
  rewards: Reward[]
  loading: boolean
}

/**
 * What was asked for, with no hint of where it ended up.
 *
 * Reward carries no virtue, rarity, value or receptacle id at all — see
 * serialize_reward in api/serializers.py — so there is nothing here for this
 * component to accidentally leak. A friend's secret gift stays masked until
 * they say `is_opened`; the owner's own rewards are never masked here, only
 * inside an unopened receptacle (the Vault handles that half).
 */
export function RewardList({ rewards, loading }: Props) {
  if (loading) return null

  if (rewards.length === 0) {
    return <p className="empty">Nothing sealed away yet.</p>
  }

  return (
    <div className="reward-list">
      <div className="label">Sealed away — {rewards.length}</div>
      {rewards.map((reward, index) => (
        <RewardRow key={index} reward={reward} />
      ))}
    </div>
  )
}

function RewardRow({ reward }: { reward: Reward }) {
  const masked = reward.is_secret && reward.text === null

  return (
    <div className="reward-row">
      <div className={masked ? 'reward-text masked-text' : 'reward-text'}>
        {masked ? 'Hidden until it opens' : reward.text}
      </div>
      <div className="reward-tags">
        {reward.is_secret ? (
          <span className="reward-tag secret">secret · {reward.friend_name}</span>
        ) : (
          <span className="reward-tag mine">yours</span>
        )}
        {reward.is_opened && <span className="reward-tag opened">opened</span>}
      </div>
      <div className="reward-when">{relativeTime(reward.created_at)}</div>
    </div>
  )
}
