import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'

import { api } from '../api'
import { DOSHAS, DOSHA_INFO, doshaComposition } from '../domain'
import type { DoshaComposition } from '../domain'
import { buildSpreads } from './codexPages'
import type { Task, Element } from '../types'

import './codex.css'

/**
 * The fourth deck section: an in-world book rather than another dark-glass
 * panel — see codex.css for why it deliberately does not match the other
 * three layouts.
 *
 * Book content lives in codexPages.tsx; this file is only the machinery that
 * turns the pages and the two figures (the dosha pies) that need live data.
 */

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

/** History is small (a handful of fragments a day) — one wide window is
 * simpler and cheaper than paging, and the endpoint is unclamped. */
const HISTORY_DAYS = 3650

/** Kept equal to the --turn-duration custom property in codex.css. */
const TURN_MS = 800

type TurnDirection = 'forward' | 'backward'

interface Turn {
  direction: TurnDirection
  nextIndex: number
}

/**
 * True when the leaf should not spin: the user asked for less motion, or the
 * viewport is narrow enough that codex.css has already stacked the two pages
 * vertically (a 3D flip of two half-width pages does not read at phone
 * width). The 640px threshold has to match that CSS breakpoint exactly, or
 * the leaf would try to rotate a book shape that no longer exists.
 */
function computePlainTurn(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return (
    window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
    window.matchMedia('(max-width: 640px)').matches
  )
}

function usePlainTurn(): boolean {
  const [plain, setPlain] = useState(computePlainTurn)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const queries = [
      window.matchMedia('(prefers-reduced-motion: reduce)'),
      window.matchMedia('(max-width: 640px)'),
    ]
    const update = () => setPlain(computePlainTurn())
    queries.forEach((q) => q.addEventListener('change', update))
    return () => queries.forEach((q) => q.removeEventListener('change', update))
  }, [])

  return plain
}

function sumFragments(tasks: Task[]): Partial<Record<Element, number>> {
  const totals: Partial<Record<Element, number>> = {}
  for (const task of tasks) {
    for (const element of Object.keys(task.fragments_awarded) as Element[]) {
      totals[element] = (totals[element] ?? 0) + (task.fragments_awarded[element] ?? 0)
    }
  }
  return totals
}

function isToday(isoDate: string): boolean {
  const date = new Date(isoDate)
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

/** Whole-percent shares that sum to exactly 100 — ordinary rounding drifts
 * off 100 the moment three shares round the same way (e.g. 33/33/33 → 99). */
function sharesOf100(values: number[]): number[] {
  const total = values.reduce((a, b) => a + b, 0)
  if (total <= 0) return values.map(() => 0)

  const raw = values.map((v) => (v / total) * 100)
  const floors = raw.map(Math.floor)
  const used = floors.reduce((a, b) => a + b, 0)
  const remainder = 100 - used

  const byFraction = raw
    .map((v, i) => ({ i, fraction: v - Math.floor(v) }))
    .sort((a, b) => b.fraction - a.fraction)

  const result = [...floors]
  for (let k = 0; k < remainder; k += 1) {
    const entry = byFraction[k]
    if (entry) result[entry.i] = (result[entry.i] ?? 0) + 1
  }
  return result
}

function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

/** A single wedge, 0deg at the top and sweeping clockwise. */
function wedgePath(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const p1 = polarPoint(cx, cy, r, startAngle)
  const p2 = polarPoint(cx, cy, r, endAngle)
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${cx} ${cy} L ${p1.x} ${p1.y} A ${r} ${r} 0 ${largeArc} 1 ${p2.x} ${p2.y} Z`
}

interface DoshaPieProps {
  heading: string
  ariaSubject: string
  composition: DoshaComposition | null
  emptyNote: string
}

function DoshaPie({ heading, ariaSubject, composition, emptyNote }: DoshaPieProps) {
  // Order matches DOSHAS exactly ('VATA','PITTA','KAPHA'), which is what
  // zips these values back up with a dosha name everywhere below.
  const values = composition ? [composition.vata, composition.pitta, composition.kapha] : []
  const total = values.reduce((a, b) => a + b, 0)

  if (composition === null) {
    return (
      <div className="dosha-chart">
        <h3>{heading}</h3>
        <p className="empty-note">Reading the ledger…</p>
      </div>
    )
  }

  if (total <= 0) {
    return (
      <div className="dosha-chart">
        <h3>{heading}</h3>
        <p className="empty-note">{emptyNote}</p>
      </div>
    )
  }

  const shares = sharesOf100(values)
  const ariaLabel = `${ariaSubject}: ${DOSHAS.map((d, i) => `${DOSHA_INFO[d].name} ${shares[i]}%`).join(', ')}`
  const cx = 60
  const cy = 60
  const r = 52

  let cursor = 0
  const wedges = DOSHAS.map((dosha, i) => {
    const value = values[i] ?? 0
    if (value <= 0) return null
    const fraction = value / total
    const startAngle = cursor * 360
    cursor += fraction
    const endAngle = cursor * 360
    const info = DOSHA_INFO[dosha]

    // A single dosha holding everything degenerates the arc math (start and
    // end land on the same point), so it gets a plain circle instead.
    if (fraction > 0.9995) {
      return <circle key={dosha} cx={cx} cy={cy} r={r} fill={info.color} stroke="#3b2f2a" strokeWidth={1.5} />
    }
    return (
      <path
        key={dosha}
        d={wedgePath(cx, cy, r, startAngle, endAngle)}
        fill={info.color}
        stroke="#3b2f2a"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
    )
  })

  return (
    <div className="dosha-chart">
      <h3>{heading}</h3>
      <svg viewBox="0 0 120 120" width={128} height={128} role="img" aria-label={ariaLabel}>
        {wedges}
      </svg>
      <div className="dosha-legend">
        {DOSHAS.map((dosha, i) => (
          <div className="row" key={dosha}>
            <span
              className="swatch"
              style={{ background: DOSHA_INFO[dosha].color }}
              aria-hidden="true"
            />
            {DOSHA_INFO[dosha].name}
            <span className="num">{shares[i]}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Codex() {
  const [tasks, setTasks] = useState<Task[] | null>(null)
  const [index, setIndex] = useState(0)
  const [turn, setTurn] = useState<Turn | null>(null)
  const plainTurn = usePlainTurn()
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .listTasks(HISTORY_DAYS)
      .then(({ tasks: list }) => {
        if (!cancelled) setTasks(list)
      })
      .catch(() => {
        if (!cancelled) setTasks([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    },
    [],
  )

  const overall = useMemo<DoshaComposition | null>(
    () => (tasks ? doshaComposition(sumFragments(tasks)) : null),
    [tasks],
  )
  const today = useMemo<DoshaComposition | null>(
    () => (tasks ? doshaComposition(sumFragments(tasks.filter((t) => isToday(t.created_at)))) : null),
    [tasks],
  )

  // Built inside the memo (not as a separate variable closed over) so its
  // only real dependencies — overall, today — are exactly what is declared.
  const spreads = useMemo(
    () =>
      buildSpreads(
        <div className="dosha-charts">
          <DoshaPie
            heading="Overall"
            ariaSubject="Overall constitution"
            composition={overall}
            emptyNote="No deeds recorded yet."
          />
          <DoshaPie
            heading="Today"
            ariaSubject="Today's constitution"
            composition={today}
            emptyNote="Today's page is still blank."
          />
        </div>,
      ),
    [overall, today],
  )
  const lastIndex = spreads.length - 1

  function goForward() {
    if (turn || index >= lastIndex) return
    const nextIndex = index + 1
    if (plainTurn) {
      setIndex(nextIndex)
      return
    }
    setTurn({ direction: 'forward', nextIndex })
    timerRef.current = window.setTimeout(() => {
      setIndex(nextIndex)
      setTurn(null)
    }, TURN_MS)
  }

  function goBackward() {
    if (turn || index <= 0) return
    const nextIndex = index - 1
    if (plainTurn) {
      setIndex(nextIndex)
      return
    }
    setTurn({ direction: 'backward', nextIndex })
    timerRef.current = window.setTimeout(() => {
      setIndex(nextIndex)
      setTurn(null)
    }, TURN_MS)
  }

  // Which content each static page shows right now. A forward turn already
  // swaps the right page underneath the leaf (revealed as the leaf lifts
  // away); a backward turn does the same to the left page. The page NOT
  // being replaced stays on the old spread until the leaf lands and covers
  // it, at which point the turn commits and this collapses back to `index`
  // for both.
  const leftIndex = turn?.direction === 'backward' ? turn.nextIndex : index
  const rightIndex = turn?.direction === 'forward' ? turn.nextIndex : index

  return (
    <div className="codex">
      <div className="book-shell">
        <div className="book">
          <div className="page left">
            {!plainTurn && (
              <button
                type="button"
                className="page-edge"
                aria-label="Previous page"
                disabled={index <= 0 || !!turn}
                onClick={goBackward}
              />
            )}
            {spreads[leftIndex]?.left}
            <span className="folio">{ROMAN[leftIndex * 2] ?? leftIndex * 2 + 1}</span>
          </div>

          <div className="spine" aria-hidden="true" />

          <div className="page right">
            {spreads[rightIndex]?.right}
            {!plainTurn && (
              <button
                type="button"
                className="page-edge"
                aria-label="Next page"
                disabled={index >= lastIndex || !!turn}
                onClick={goForward}
              />
            )}
            <span className="folio">{ROMAN[rightIndex * 2 + 1] ?? rightIndex * 2 + 2}</span>
          </div>

          {turn && (
            <div
              className={turn.direction === 'forward' ? 'leaf forward' : 'leaf backward'}
              aria-hidden="true"
              style={{ '--turn-duration': `${TURN_MS}ms` } as CSSProperties}
            >
              <div className="leaf-face leaf-front">
                {turn.direction === 'forward' ? spreads[index]?.right : spreads[index]?.left}
              </div>
              <div className="leaf-face leaf-back">
                {turn.direction === 'forward'
                  ? spreads[turn.nextIndex]?.left
                  : spreads[turn.nextIndex]?.right}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="controls">
        <button type="button" className="btn-ghost" disabled={index <= 0 || !!turn} onClick={goBackward}>
          ← Previous
        </button>
        <span className="folio-count">
          Spread {index + 1} of {spreads.length}
        </span>
        <button
          type="button"
          className="btn-ghost"
          disabled={index >= lastIndex || !!turn}
          onClick={goForward}
        >
          Next →
        </button>
      </div>
    </div>
  )
}
