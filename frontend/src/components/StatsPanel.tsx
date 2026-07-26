import { label } from '../domain'
import { useGameStore } from '../state/store'
import { TASK_VIRTUES } from '../types'

export function StatsPanel() {
  const stats = useGameStore((s) => s.stats)
  if (!stats) return null

  const activeDays = Object.keys(stats.per_day).length
  const totalTasks = Object.values(stats.per_day).reduce((sum, count) => sum + count, 0)
  const maxMean = Math.max(1, ...TASK_VIRTUES.map((virtue) => stats.virtue_means[virtue] ?? 0))

  return (
    <section className="panel">
      <h2>Your month</h2>
      <p className="muted small">
        <strong>{stats.streak}</strong> day streak · {totalTasks} task
        {totalTasks === 1 ? '' : 's'} across {activeDays} day{activeDays === 1 ? '' : 's'}
      </p>

      <h3>What you have been calling on</h3>
      <ul className="bars">
        {TASK_VIRTUES.map((virtue) => {
          const mean = stats.virtue_means[virtue] ?? 0
          return (
            <li key={virtue}>
              <span className="bar-label">{label(virtue)}</span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${(mean / maxMean) * 100}%` }} />
              </span>
              <span className="bar-value">{Math.round(mean)}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
