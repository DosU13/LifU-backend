import { useGameStore } from '../state/store'

export function WalletBadge() {
  const coins = useGameStore((s) => s.coins)
  return (
    <span className="wallet" title="Coins">
      ◈ {coins.toLocaleString()}
    </span>
  )
}
