import { useEffect, useMemo, useState } from 'react'

import { api } from '../api'
import { ELEMENT_TASK_VIRTUE, label } from '../domain'
import { useGameStore } from '../state/store'
import { collectableIcon } from '../ui/Icon'
import { Reveal } from '../ui/Overlay'
import { relativeTime } from '../ui/relativeTime'
import { useReveal } from '../ui/useReveal'
import type { Element, Task } from '../types'

import './ledger.css'

const GREETINGS = [
  'Another great accomplishment:',
  'What did you conquer?',
  'Go on — brag a little.',
  'Something moved forward today.',
  'Tell me what you finished.',
  'The day owes you nothing. What did you take?',
]

const FIRST_PAGE = 4
const EXPANDED = 14

export function Ledger() {
  const completeTask = useGameStore((s) => s.completeTask)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [tasks, setTasks] = useState<Task[]>([])
  const [expanded, setExpanded] = useState(false)
  const reveal = useReveal()

  // Picked once per mount rather than per render, or it would change on every
  // keystroke in the textarea.
  const greeting = useMemo(
    () => GREETINGS[Math.floor(Math.random() * GREETINGS.length)] ?? GREETINGS[0],
    [],
  )

  useEffect(() => {
    void api
      .listTasks()
      .then(({ tasks: list }) => setTasks(list))
      .catch(() => setTasks([]))
  }, [])

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || busy) return

    setBusy(true)
    const result = await completeTask(trimmed)
    setBusy(false)
    if (!result) return

    setText('')
    // Replay exactly what the server paid out, in the order it sent. The
    // reveal must never invent a count of its own.
    reveal.show(
      Object.entries(result.fragments_awarded).map(([element, count]) => {
        const paidFor = ELEMENT_TASK_VIRTUE[element as Element]
        return {
          image: collectableIcon(element as Element, 'FRAGMENT'),
          amount: `×${count}`,
          title: `${label(element)} Fragment`,
          ...(paidFor ? { note: label(paidFor).toLowerCase() } : {}),
        }
      }),
    )

    void api
      .listTasks()
      .then(({ tasks: list }) => setTasks(list))
      .catch(() => undefined)
  }

  const visible = tasks.slice(0, expanded ? EXPANDED : FIRST_PAGE)

  return (
    <div className="ledger">
      <h1 className="greeting">{greeting}</h1>

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="What did you get done?"
          aria-label="What did you get done?"
          rows={4}
          // Enter alone would fight multi-line descriptions, so submit is
          // explicit or Ctrl/Cmd+Enter.
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              void onSubmit(event)
            }
          }}
        />
        <div className="composer-foot">
          <span className="hint">It gets read, weighed, and paid in elements.</span>
          <button type="submit" className="btn-primary" disabled={!text.trim() || busy}>
            {busy ? 'Weighing…' : 'Claim'}
          </button>
        </div>
      </form>

      <div className="recent">
        <div className="label">Recently done</div>

        {tasks.length === 0 ? (
          <p className="empty">Nothing logged yet. The first one is the hardest.</p>
        ) : (
          <>
            {visible.map((task) => (
              <TaskRow key={task.id} task={task} />
            ))}
            {tasks.length > FIRST_PAGE && !expanded && (
              <button type="button" className="more" onClick={() => setExpanded(true)}>
                · · · more · · ·
              </button>
            )}
          </>
        )}
      </div>

      {reveal.showing && (
        <Reveal
          queue={reveal.queue}
          index={reveal.index}
          onAdvance={reveal.advance}
          onSkip={reveal.skip}
        />
      )}
    </div>
  )
}

function TaskRow({ task }: { task: Task }) {
  const drops = Object.entries(task.fragments_awarded)

  return (
    <div className="task">
      <div className="task-text" title={task.text}>
        {task.text}
      </div>
      <div className="task-meta">
        <div className="drops">
          {drops.map(([element, count]) => (
            <span className="drop" key={element}>
              <img
                src={collectableIcon(element as Element, 'FRAGMENT')}
                width={21}
                height={21}
                alt=""
              />
              {count}
            </span>
          ))}
        </div>
        <div className="task-when">{relativeTime(task.created_at)}</div>
      </div>
    </div>
  )
}
