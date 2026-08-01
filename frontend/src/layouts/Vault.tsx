import { useMemo, useState } from 'react'

import { COLLECTABLE_RARITIES, ELEMENTS, stockKey } from '../types'
import type { CollectableRarity, Element, Receptacle, Stocks } from '../types'
import { keyForReceptacle, label, nextRarity, sellPrice } from '../domain'
import { useGameStore } from '../state/store'
import { collectableIcon, receptacleIcon } from '../ui/Icon'
import { Modal, Reveal } from '../ui/Overlay'
import { useReveal } from '../ui/useReveal'
import { detectOp, maxRepeats } from './bench'
import type { BenchItem } from './bench'
import { RecipeInfo } from './RecipeInfo'

import './vault.css'

type Inspected =
  | { type: 'collectable'; element: Element; rarity: CollectableRarity }
  | { type: 'receptacle'; receptacle: Receptacle }

export function Vault() {
  const stocks = useGameStore((s) => s.stocks)
  const dropped = useGameStore((s) => s.droppedReceptacles)
  const mergeUp = useGameStore((s) => s.mergeUp)
  const mergeHarmony = useGameStore((s) => s.mergeHarmony)
  const combine = useGameStore((s) => s.combine)
  const openReceptacle = useGameStore((s) => s.openReceptacle)

  const [bench, setBench] = useState<BenchItem[]>([])
  const [quantity, setQuantity] = useState(1)
  const [inspected, setInspected] = useState<Inspected | null>(null)
  const [busy, setBusy] = useState(false)
  const reveal = useReveal()

  const op = useMemo(() => detectOp(bench, stocks), [bench, stocks])
  const limit = useMemo(() => maxRepeats(op, stocks), [op, stocks])
  const repeats = Math.max(1, Math.min(quantity, Math.max(limit, 1)))

  const held = useMemo(
    () =>
      ELEMENTS.flatMap((element) =>
        COLLECTABLE_RARITIES.map((rarity) => ({
          element,
          rarity,
          count: stocks[stockKey(element, rarity)] ?? 0,
        })),
      ).filter((entry) => entry.count > 0),
    [stocks],
  )

  function addToBench(item: BenchItem) {
    // Five is the largest any recipe needs, so anything beyond it is a mistake.
    setBench((current) => (current.length >= 5 ? current : [...current, item]))
  }

  async function run() {
    if (op.kind === 'blocked' || busy) return
    setBusy(true)

    try {
      if (op.kind === 'open') {
        const ok = await openReceptacle(op.receptacle.id)
        if (ok) {
          reveal.show([
            {
              image: receptacleIcon(op.receptacle.virtue, op.receptacle.rarity),
              title: `${label(op.receptacle.rarity)} of ${label(op.receptacle.virtue)}`,
              note: 'opened',
            },
          ])
        }
      } else {
        // The endpoints each perform one operation, so a quantity is that many
        // sequential calls rather than a bulk request the server does not offer.
        for (let i = 0; i < repeats; i += 1) {
          const ok =
            op.kind === 'merge'
              ? await mergeUp(op.element, op.rarity)
              : op.kind === 'harmony'
                ? await mergeHarmony(op.rarity)
                : await combine(op.a, op.b, op.rarity)
          if (!ok) break
        }
      }
      setBench([])
      setQuantity(1)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="vault">
      <div className="panel hoard">
        {held.length === 0 && dropped.length === 0 ? (
          <p className="empty">Nothing yet. Log something you did and the elements start arriving.</p>
        ) : null}

        {held.length > 0 && (
          <>
            <div className="label">Collectables</div>
            <div className="hoard-grid">
              {held.map(({ element, rarity, count }) => (
                <button
                  type="button"
                  key={stockKey(element, rarity)}
                  className="item"
                  // data-name drives the hover tooltip, which is CSS-only and
                  // therefore invisible to assistive tech; the label is what
                  // actually names the control.
                  data-name={`${label(element)} ${label(rarity)}`}
                  aria-label={`${label(element)} ${label(rarity)}, ${count} held`}
                  onClick={() => addToBench({ type: 'collectable', element, rarity })}
                  onDoubleClick={() => setInspected({ type: 'collectable', element, rarity })}
                >
                  <img src={collectableIcon(element, rarity)} width={50} height={50} alt="" />
                  <span className="n">{count}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {dropped.length > 0 && (
          <>
            <div className="label">Receptacles — sealed</div>
            <div className="hoard-grid">
              {dropped.map((receptacle) => {
                const key = keyForReceptacle(receptacle.virtue, receptacle.rarity)
                const hasKey = (stocks[stockKey(key.element, key.rarity)] ?? 0) > 0
                return (
                  <button
                    type="button"
                    key={receptacle.id}
                    className={hasKey ? 'item' : 'item locked'}
                    data-name={`${label(receptacle.rarity)} of ${label(receptacle.virtue)}`}
                    aria-label={
                      `${label(receptacle.rarity)} of ${label(receptacle.virtue)}, ` +
                      (hasKey ? 'key ready' : 'locked')
                    }
                    onClick={() => addToBench({ type: 'receptacle', receptacle })}
                    onDoubleClick={() => setInspected({ type: 'receptacle', receptacle })}
                  >
                    <span className={hasKey ? 'ready' : 'lock'} aria-hidden="true">
                      {hasKey ? '●' : '🔒'}
                    </span>
                    <img
                      src={receptacleIcon(receptacle.virtue, receptacle.rarity)}
                      width={50}
                      height={50}
                      alt=""
                    />
                  </button>
                )
              })}
            </div>
          </>
        )}
      </div>

      <div className="panel bench">
        <div className="slots">
          {bench.length === 0 ? (
            <span className="placeholder">
              Click items to load the bench · double-click to inspect
            </span>
          ) : (
            bench.map((item, index) => (
              <button
                type="button"
                className="item"
                key={index}
                title="Take it back off"
                onClick={() => setBench((c) => c.filter((_, i) => i !== index))}
              >
                <img
                  src={
                    item.type === 'collectable'
                      ? collectableIcon(item.element, item.rarity)
                      : receptacleIcon(item.receptacle.virtue, item.receptacle.rarity)
                  }
                  width={44}
                  height={44}
                  alt=""
                />
              </button>
            ))
          )}
        </div>

        {op.kind !== 'open' && op.kind !== 'blocked' && limit > 1 && (
          <input
            className="qty"
            type="number"
            min={1}
            max={limit}
            value={quantity}
            aria-label={`How many times (up to ${limit})`}
            onChange={(event) => setQuantity(Number(event.target.value) || 1)}
          />
        )}

        <button
          type="button"
          className="btn-violet"
          disabled={op.kind === 'blocked' || busy}
          onClick={() => void run()}
        >
          {busy ? 'Working…' : op.label}
          {op.kind !== 'blocked' && op.kind !== 'open' && repeats > 1 ? ` ×${repeats}` : ''}
        </button>

        <RecipeInfo />
      </div>

      {/* A blocked bench says why, rather than leaving a dead button. */}
      {op.kind === 'blocked' && bench.length > 0 && <p className="bench-reason">{op.reason}</p>}

      {inspected && (
        <ItemDetail
          inspected={inspected}
          stocks={stocks}
          onClose={() => setInspected(null)}
          onOpen={(receptacle) => {
            setInspected(null)
            setBench([{ type: 'receptacle', receptacle }])
          }}
        />
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

function ItemDetail({
  inspected,
  stocks,
  onClose,
  onOpen,
}: {
  inspected: Inspected
  stocks: Stocks
  onClose: () => void
  onOpen: (receptacle: Receptacle) => void
}) {
  const sell = useGameStore((s) => s.sell)

  if (inspected.type === 'receptacle') {
    const { receptacle } = inspected
    const key = keyForReceptacle(receptacle.virtue, receptacle.rarity)
    const hasKey = (stocks[stockKey(key.element, key.rarity)] ?? 0) > 0

    return (
      <Modal onClose={onClose} labelledBy="detail-title">
        <div className="detail-card">
          <img
            src={receptacleIcon(receptacle.virtue, receptacle.rarity)}
            width={150}
            height={150}
            alt=""
          />
          <h2 id="detail-title">
            {label(receptacle.rarity)} of {label(receptacle.virtue)}
          </h2>
          <div className="label">sealed</div>
          <p className="desc">
            Something you wanted, sealed away until you earn the way in. What is inside
            stays hidden until it opens.
          </p>
          <div className={hasKey ? 'keyline have' : 'keyline need'}>
            <img src={collectableIcon(key.element, key.rarity)} width={32} height={32} alt="" />
            <span>
              {hasKey
                ? `Ready — one ${label(key.element)} ${label(key.rarity)} will open this`
                : `Needs one ${label(key.element)} ${label(key.rarity)} — you have none yet`}
            </span>
          </div>
          <div className="detail-actions">
            {hasKey && (
              <button type="button" className="btn-primary" onClick={() => onOpen(receptacle)}>
                Open it
              </button>
            )}
            <button type="button" className="btn-ghost" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </Modal>
    )
  }

  const { element, rarity } = inspected
  const count = stocks[stockKey(element, rarity)] ?? 0
  const next = nextRarity(rarity)
  const price = sellPrice(element, rarity)

  return (
    <Modal onClose={onClose} labelledBy="detail-title">
      <div className="detail-card">
        <img src={collectableIcon(element, rarity)} width={150} height={150} alt="" />
        <h2 id="detail-title">
          {label(element)} {label(rarity)}
        </h2>
        <div className="label">
          {count} held · sells for {price}
        </div>
        <p className="desc">
          {next
            ? `Three of these merge into one ${label(element)} ${label(next)}.`
            : 'The highest rarity there is.'}
        </p>
        <div className="detail-actions">
          <button
            type="button"
            className="btn-ghost"
            disabled={count < 1}
            onClick={() => {
              void sell(element, rarity, 1)
              onClose()
            }}
          >
            Sell one for {price}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </Modal>
  )
}
