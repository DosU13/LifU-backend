import { useState } from 'react'

import { useGameStore } from '../state/store'

export function TaskComposer() {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const completeTask = useGameStore((s) => s.completeTask)

  const canSubmit = text.trim().length > 0 && !busy

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    const ok = await completeTask(text.trim())
    setBusy(false)
    if (ok) setText('')
  }

  return (
    <section className="panel">
      <h2>What did you do?</h2>
      <p className="muted small">
        Describe something you finished. It is valued, and pays out fragments of the elements it
        called on.
      </p>
      <form onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="Went for a 10km run even though it was raining"
          aria-label="Task description"
        />
        <button type="submit" disabled={!canSubmit}>
          {busy ? 'Valuing…' : 'Log it'}
        </button>
      </form>
    </section>
  )
}
