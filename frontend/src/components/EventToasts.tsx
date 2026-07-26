import { useGameStore } from '../state/store'

export function EventToasts() {
  const events = useGameStore((s) => s.events)
  const dismiss = useGameStore((s) => s.dismissEvent)
  if (events.length === 0) return null

  return (
    <ul className="toasts" aria-live="polite">
      {events.map((event) => (
        <li key={event.id} className={`toast ${event.kind}`}>
          <span>{event.message}</span>
          <button type="button" className="mini" onClick={() => dismiss(event.id)} aria-label="Dismiss">
            ×
          </button>
        </li>
      ))}
    </ul>
  )
}
