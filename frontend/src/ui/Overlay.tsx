import { useEffect } from 'react'
import type { ReactNode } from 'react'

import './overlay.css'

/**
 * The full-screen veil, in two flavours.
 *
 * `Modal` is a plain dismissible panel. `Reveal` walks a queue of prizes one
 * at a time, which is what every payout in the game uses: task drops, merge
 * results, and whatever a treasure finally hands over.
 *
 * The queue is always server-supplied. Nothing here invents how many items
 * there are or which one you got — see the elimination sequencer in the
 * treasury for why that separation matters.
 */

interface ModalProps {
  onClose: () => void
  children: ReactNode
  labelledBy?: string
}

export function Modal({ onClose, children, labelledBy }: ModalProps) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="veil"
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
      // Only a click on the backdrop itself dismisses; one that started inside
      // the card and drifted out should not.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      {children}
    </div>
  )
}

export interface Prize {
  /** Icon URL — resolved by the caller, which knows what kind of thing this is. */
  image: string
  title: string
  /** e.g. "×13" — omitted for single things like a receptacle. */
  amount?: string
  /** The quiet line underneath: which virtue paid, or what happens next. */
  note?: string
}

interface RevealProps {
  queue: Prize[]
  index: number
  onAdvance: () => void
  onSkip: () => void
}

export function Reveal({ queue, index, onAdvance, onSkip }: RevealProps) {
  const prize = queue[index]
  if (!prize) return null

  const hasMore = queue.length > 1

  return (
    <div className="veil" role="dialog" aria-modal="true" aria-live="polite">
      <div className="rays" aria-hidden="true" />

      <div className="prize" key={index}>
        <img src={prize.image} alt="" width={190} height={190} />
        {prize.amount && <div className="prize-amount">{prize.amount}</div>}
        <div className="prize-title">{prize.title}</div>
        {prize.note && <div className="prize-note">{prize.note}</div>}
      </div>

      {hasMore && (
        <div className="queue-dots" aria-hidden="true">
          {queue.map((_, i) => (
            <i key={i} className={i <= index ? 'on' : undefined} />
          ))}
        </div>
      )}

      <div className="veil-actions">
        {hasMore && (
          <button type="button" className="btn-ghost" onClick={onSkip}>
            Skip all
          </button>
        )}
        <button type="button" className="btn-primary" onClick={onAdvance} autoFocus>
          {index + 1 >= queue.length ? 'Done' : 'Next'}
        </button>
      </div>
    </div>
  )
}
