import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'

import { label, revealTier } from '../domain'
import { useGameStore } from '../state/store'
import { collectableIcon, receptacleIcon, treasureIcon } from '../ui/Icon'
import { Modal, Reveal } from '../ui/Overlay'
import { useReveal } from '../ui/useReveal'
import { planElimination } from './elimination'
import type { Treasure, TreasureContentPreview } from '../types'

import './treasury.css'

/** Orbiting sparks around a mythic drop. Six is plenty at floater size — the
 * reveal earns fourteen, but this is ambient scenery, not the payoff. */
const FLOATER_MOTE_COUNT = 6

function FloaterMotes() {
  return (
    <div className="floater-motes" aria-hidden="true">
      {Array.from({ length: FLOATER_MOTE_COUNT }, (_, i) => (
        <i key={i} style={{ '--i': i } as CSSProperties} />
      ))}
    </div>
  )
}

/** How long each beat of the elimination lasts. Slow on purpose — the wait is the point. */
const SHIVER_MS = 1400
const PER_ELIMINATION_MS = 780
const BEFORE_WINNER_MS = 700
const AFTER_WINNER_MS = 1300

interface Sequence {
  contents: TreasureContentPreview[]
  winner: number
  /** Indices already darkened. */
  out: number[]
  crowned: boolean
}

export function Treasury() {
  const treasures = useGameStore((s) => s.treasures)
  const coins = useGameStore((s) => s.coins)
  const selectedId = useGameStore((s) => s.selectedTreasureId)
  const selectTreasure = useGameStore((s) => s.selectTreasure)
  const buyTreasure = useGameStore((s) => s.buyTreasure)
  const discardTreasure = useGameStore((s) => s.discardTreasure)

  const [sequence, setSequence] = useState<Sequence | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmingDiscard, setConfirmingDiscard] = useState(false)
  const reveal = useReveal()
  const timers = useRef<number[]>([])
  // What "Skip" fast-forwards to: the elimination countdown is the only thing
  // a skip should cut short. The prize it was building up to must still show
  // — otherwise a skip mid-buy silently eats the answer to "what did I get".
  const pendingFinish = useRef<(() => void) | null>(null)

  // A sequence left running after unmount would set state on a dead component.
  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout)
    },
    [],
  )

  const selected = treasures.find((t) => t.id === selectedId) ?? null
  const rolling = sequence !== null
  const contents = sequence?.contents ?? selected?.contents ?? []

  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      timers.current.push(window.setTimeout(resolve, ms))
    })

  async function buy() {
    if (!selected || busy || rolling) return
    setBusy(true)

    // Snapshot before the store refreshes: the contents list is about to
    // change underneath, and the animation has to run on what was on screen.
    const snapshot = selected.contents
    const result = await buyTreasure(selected.id)
    setBusy(false)
    if (!result) return

    // Match on dropped_rarity, not drop.rarity. Opening a receptacle triggers
    // the 27:9:3:1 recalculation, so drop.rarity is what it was *relabelled*
    // to afterwards, while the treasure on screen still shows the rarity it
    // was won at. Using drop.rarity makes the match fail and the animation
    // silently skip.
    const plan = planElimination(snapshot, {
      virtue: result.drop.virtue,
      rarity: result.dropped_rarity,
    })
    const finish = () => {
      pendingFinish.current = null
      setSequence(null)
      reveal.show([
        {
          image: receptacleIcon(result.drop.virtue, result.drop.rarity),
          title: `${label(result.drop.rarity)} of ${label(result.drop.virtue)}`,
          // Keyed off the same rarity the title prints, not dropped_rarity —
          // the spectacle has to agree with the name next to it.
          tier: revealTier(result.drop.rarity),
          note: result.was_pity ? 'pity paid out — now find its key' : 'now find its key',
        },
      ])
    }

    if (!plan) {
      finish()
      return
    }

    // Reachable even mid-countdown: skip() clears the timers below, which
    // permanently strands this function on its next `await wait(...)` — so
    // finish() must also be callable from the outside, not just at the end
    // of this straight-line run.
    pendingFinish.current = finish
    setSequence({ contents: snapshot, winner: plan.winner, out: [], crowned: false })

    await wait(SHIVER_MS)
    for (const index of plan.order) {
      await wait(PER_ELIMINATION_MS)
      setSequence((current) =>
        current ? { ...current, out: [...current.out, index] } : current,
      )
    }
    await wait(BEFORE_WINNER_MS)
    setSequence((current) => (current ? { ...current, crowned: true } : current))
    await wait(AFTER_WINNER_MS)
    finish()
  }

  function skip() {
    timers.current.forEach(clearTimeout)
    timers.current = []
    // Skips the countdown, not the payoff — the prize still has to show,
    // otherwise buying a treasure and hitting skip would tell you nothing.
    pendingFinish.current?.()
  }

  async function confirmDiscard() {
    if (!selected) return
    setConfirmingDiscard(false)
    await discardTreasure(selected.id)
  }

  const tooPoor = selected !== null && coins < selected.price

  return (
    <div className="treasury">
      <div className="chests">
        {treasures.length === 0 && <p className="empty">No treasures right now.</p>}
        {treasures.map((treasure) => (
          <TreasureCard
            key={treasure.id}
            treasure={treasure}
            selected={treasure.id === selectedId}
            disabled={rolling}
            onSelect={() => selectTreasure(treasure.id)}
          />
        ))}
      </div>

      <div className="contents">
        {contents.length === 0 ? (
          <span className="empty">Pick a treasure to see what is inside</span>
        ) : (
          contents.map((item, index) => {
            const isOut = sequence?.out.includes(index) ?? false
            const isWinner = sequence?.crowned === true && sequence.winner === index
            const tier = revealTier(item.rarity)
            const icon = receptacleIcon(item.virtue, item.rarity)
            return (
              <div
                key={index}
                className={
                  'floater' +
                  (tier ? ` tier-${tier}` : '') +
                  (rolling && !isOut && !isWinner ? ' shiver' : '') +
                  (isOut ? ' out' : '') +
                  (isWinner ? ' won' : '')
                }
              >
                {/* Everything in here is scenery around the icon — the rings
                    are pseudo-elements on .stage itself (see treasury.css),
                    so only the effects that need a per-item icon URL or a
                    dynamic particle count are real nodes. All of it is
                    aria-hidden; the label below says the same thing in
                    words. */}
                <div className="stage">
                  <img src={icon} alt={`${label(item.rarity)} of ${label(item.virtue)}`} />
                  {tier && (
                    <div
                      className="floater-sheen"
                      aria-hidden="true"
                      style={{ maskImage: `url(${icon})`, WebkitMaskImage: `url(${icon})` }}
                    />
                  )}
                  {tier === 'mythic' && <FloaterMotes />}
                  {isWinner && <div className="floater-shock" aria-hidden="true" />}
                </div>
                <span className="fname">
                  {label(item.rarity)} of {label(item.virtue)}
                </span>
              </div>
            )
          })
        )}
      </div>

      <div className="buy-row">
        {rolling ? (
          <>
            <span className="rolling">rolling…</span>
            <button type="button" className="btn-ghost" onClick={skip}>
              Skip
            </button>
          </>
        ) : (
          selected && (
            <>
              <button
                type="button"
                className="btn-primary"
                disabled={busy || tooPoor}
                onClick={() => void buy()}
              >
                {busy ? 'Opening…' : `Buy — ${selected.price}`}
              </button>
              {tooPoor && <span className="hint">Not enough coins.</span>}
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setConfirmingDiscard(true)}
                title="Once a day, send a treasure's contents back to the pool"
              >
                Let it go
              </button>
            </>
          )
        )}
      </div>

      {confirmingDiscard && selected && (
        <Modal onClose={() => setConfirmingDiscard(false)} labelledBy="discard-title">
          <div className="detail-card">
            <h2 id="discard-title">Let this treasure go?</h2>
            <p className="desc">
              Everything sealed inside goes back to the pool — {selected.contents.length}{' '}
              receptacle{selected.contents.length === 1 ? '' : 's'} — and a new treasure takes
              the slot. This can only be undone once a day, across all three slots.
            </p>
            <div className="detail-actions">
              <button type="button" className="btn-primary" onClick={() => void confirmDiscard()}>
                Yes, let it go
              </button>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setConfirmingDiscard(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}

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

function TreasureCard({
  treasure,
  selected,
  disabled,
  onSelect,
}: {
  treasure: Treasure
  selected: boolean
  disabled: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={selected ? 'chest on' : 'chest'}
      disabled={disabled}
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={`Treasure in slot ${treasure.slot + 1}, ${treasure.price} coins, ${treasure.contents.length} sealed`}
    >
      <img src={treasureIcon()} width={52} height={52} alt="" />
      <span className="cprice">
        <img src={collectableIcon('SUN', 'FRAGMENT')} width={13} height={13} alt="" />
        {/* The server's fixed price. It is set when the treasure is generated and
            must not be recomputed from the contents, or emptying one would make
            it cheaper. */}
        {treasure.price}
      </span>
      <span className="ccount">{treasure.contents.length} sealed</span>
    </button>
  )
}
