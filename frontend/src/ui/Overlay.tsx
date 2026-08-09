import { useEffect } from 'react'
import type { CSSProperties, ReactNode } from 'react'

import type { RevealTier } from '../domain'

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
  /**
   * Extra spectacle for the top three rarities, from `revealTier`. Spelled
   * `| undefined` rather than left bare so callers can pass that function's
   * result straight through — `exactOptionalPropertyTypes` rejects an
   * explicit `undefined` for a plainly optional property.
   */
  tier?: RevealTier | undefined
}

/** More of them the rarer it is; the CSS staggers each one off its index. */
const MOTE_COUNT: Record<RevealTier, number> = { gilded: 6, radiant: 10, mythic: 14 }
const EMBER_COUNT = 18

function particles(className: string, count: number) {
  return (
    <div className={className} aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <i key={i} style={{ '--i': i } as CSSProperties} />
      ))}
    </div>
  )
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
  const { tier } = prize
  const loud = tier === 'radiant' || tier === 'mythic'

  return (
    <div
      className={tier ? `veil tier-${tier}` : 'veil'}
      role="dialog"
      aria-modal="true"
      aria-live="polite"
    >
      {/* All of this is decoration and says nothing the text below does not,
          so it stays out of the accessibility tree entirely. */}
      <div className="rays" aria-hidden="true" />
      {loud && <div className="rays violet" aria-hidden="true" />}
      {tier === 'mythic' && (
        <>
          {/* Keyed so the one-shot flash fires per prize. The veil itself
              survives a queue advance, and an animation on a surviving
              element does not restart. */}
          <div className="flash" key={`flash-${index}`} aria-hidden="true" />
          {particles('embers', EMBER_COUNT)}
        </>
      )}

      <div className="prize-frame" key={index}>
        <div className="prize">
          {loud && <div className="shock" aria-hidden="true" />}
          <img src={prize.image} alt="" width={190} height={190} />
          {tier && (
            <div
              className="sheen"
              aria-hidden="true"
              // Masked by the icon itself, so the shimmer follows its
              // silhouette instead of sweeping a bare square across it.
              style={{
                maskImage: `url(${prize.image})`,
                WebkitMaskImage: `url(${prize.image})`,
              }}
            />
          )}
          {tier && particles('motes', MOTE_COUNT[tier])}
          {prize.amount && <div className="prize-amount">{prize.amount}</div>}
          <div className="prize-title">{prize.title}</div>
          {prize.note && <div className="prize-note">{prize.note}</div>}
        </div>
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
