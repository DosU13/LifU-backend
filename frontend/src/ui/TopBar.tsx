import { useGameStore } from '../state/store'
import { useSessionStore } from '../state/session'
import { iconForStockKey } from './Icon'

/**
 * Fixed across every layout, because coins matter on the vault and the
 * treasury alike and scrolling back to check would be tedious.
 */
export function TopBar({ showAdminLink = true }: { showAdminLink?: boolean }) {
  const coins = useGameStore((s) => s.coins)
  const isTrial = useSessionStore((s) => s.isTrial)

  return (
    <div className="topbar">
      <div className="brand">LIFU</div>
      <div className="topbar-right">
        {isTrial && <span className="pill trial">Trial — nothing is saved</span>}
        <span className="pill">
          <img src={iconForStockKey('SUN_FRAGMENT')} width={20} height={20} alt="Coins" />
          <b>{coins.toLocaleString()}</b>
        </span>
        {/* A trial has no rewards of its own to manage. */}
        {showAdminLink && !isTrial && (
          <a className="pill" href="/admin">
            Admin
          </a>
        )}
      </div>
    </div>
  )
}
