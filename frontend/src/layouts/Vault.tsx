import { useEffect, useMemo, useState } from 'react'

import { api } from '../api'
import { COLLECTABLE_RARITIES, ELEMENTS, stockKey } from '../types'
import type { CollectableRarity, Element, Receptacle, Stocks } from '../types'
import { keyForReceptacle, label, nextRarity, revealTier, sellPrice } from '../domain'
import type { RevealTier } from '../domain'
import { useGameStore } from '../state/store'
import { collectableFlavor, receptacleFlavor } from '../ui/flavorText'
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

/** Encodes a bench item onto the HTML5 drag payload, and back again on drop. */
function dragPayload(item: BenchItem): string {
  return item.type === 'collectable'
    ? `collectable:${item.element}:${item.rarity}`
    : `receptacle:${item.receptacle.id}`
}

/**
 * Rarity dressing borrows the reveal's vocabulary on purpose — what glows in
 * the hoard is what will flash when it finally opens.
 */
function tileClass(base: string, tier: RevealTier | undefined): string {
  return tier ? `${base} tier-${tier}` : base
}

/**
 * The foil sweep from the reveal, shrunk onto a tile and masked by the icon.
 * Only rendered for tiles that have a tier — the grid runs to ninety-odd of
 * these, and the CSS leaves it idle until the tile is hovered.
 */
function TileSheen({ icon }: { icon: string }) {
  return (
    <i
      className="tile-sheen"
      aria-hidden="true"
      style={{ maskImage: `url(${icon})`, WebkitMaskImage: `url(${icon})` }}
    />
  )
}

export function Vault() {
  const stocks = useGameStore((s) => s.stocks)
  const dropped = useGameStore((s) => s.droppedReceptacles)
  const mergeUp = useGameStore((s) => s.mergeUp)
  const mergeHarmony = useGameStore((s) => s.mergeHarmony)
  const combine = useGameStore((s) => s.combine)
  const sell = useGameStore((s) => s.sell)
  const openReceptacle = useGameStore((s) => s.openReceptacle)

  const [bench, setBench] = useState<BenchItem[]>([])
  const [quantity, setQuantity] = useState(1)
  const [sellQuantity, setSellQuantity] = useState(1)
  const [inspected, setInspected] = useState<Inspected | null>(null)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [opened, setOpened] = useState<Receptacle[]>([])
  const reveal = useReveal()

  const op = useMemo(() => detectOp(bench, stocks), [bench, stocks])
  const limit = useMemo(() => maxRepeats(op, stocks), [op, stocks])
  const repeats = Math.max(1, Math.min(quantity, Math.max(limit, 1)))

  const held = useMemo(
    () =>
      COLLECTABLE_RARITIES.flatMap((rarity) =>
        ELEMENTS.map((element) => ({
          element,
          rarity,
          count: stocks[stockKey(element, rarity)] ?? 0,
        })),
      ).filter((entry) => entry.count > 0),
    [stocks],
  )

  function refreshOpened() {
    void api
      .listReceptacles('OPENED')
      .then(({ receptacles }) => setOpened(receptacles))
      .catch(() => undefined)
  }

  useEffect(refreshOpened, [])

  // One collectable alone can't merge, harmonise or combine — that's the
  // moment to offer selling it instead of a dead "blocked" button.
  const soleCollectable =
    bench.length === 1 && bench[0]!.type === 'collectable'
      ? (bench[0] as Extract<BenchItem, { type: 'collectable' }>)
      : null
  const soleHeld = soleCollectable
    ? (stocks[stockKey(soleCollectable.element, soleCollectable.rarity)] ?? 0)
    : 0
  const sellCount = Math.max(1, Math.min(sellQuantity, Math.max(soleHeld, 1)))

  function addToBench(item: BenchItem) {
    // Five is the largest any recipe needs, so anything beyond it is a mistake.
    setBench((current) => (current.length >= 5 ? current : [...current, item]))
  }

  function dropOnBench(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragOver(false)
    const [kind, a, b] = event.dataTransfer.getData('text/plain').split(':')
    if (kind === 'collectable' && a && b) {
      addToBench({ type: 'collectable', element: a as Element, rarity: b as CollectableRarity })
    } else if (kind === 'receptacle' && a) {
      const receptacle = dropped.find((r) => r.id === a)
      if (receptacle) addToBench({ type: 'receptacle', receptacle })
    }
  }

  async function runSell() {
    if (!soleCollectable || busy) return
    setBusy(true)
    try {
      const { element, rarity } = soleCollectable
      const gained = sellPrice(element, rarity) * sellCount
      const ok = await sell(element, rarity, sellCount)
      if (ok) {
        reveal.show([
          {
            image: collectableIcon('SUN', 'FRAGMENT'),
            amount: `+${gained}`,
            title: 'Coins',
            note: `sold ${sellCount} ${label(element)} ${label(rarity)}${sellCount > 1 ? 's' : ''}`,
          },
        ])
      }
      setBench([])
      setSellQuantity(1)
    } finally {
      setBusy(false)
    }
  }

  async function run() {
    if (op.kind === 'blocked' || busy) return
    setBusy(true)

    try {
      if (op.kind === 'open') {
        const result = await openReceptacle(op.receptacle.id)
        if (result) {
          const { receptacle: opened } = result
          reveal.show([
            {
              image: receptacleIcon(opened.virtue, opened.rarity),
              title: `${label(opened.rarity)} of ${label(opened.virtue)}`,
              tier: revealTier(opened.rarity),
              note:
                opened.reward_text ??
                opened.content?.text ??
                `+${result.coins_gained} coins`,
            },
          ])
          refreshOpened()
        }
      } else if (op.kind === 'harmony') {
        const result = await mergeHarmony(op.rarity)
        if (result) {
          reveal.show([
            {
              image: collectableIcon('HARMONY', op.rarity),
              amount: `×${result.yield}`,
              title: `${label(op.rarity)} Harmony`,
              tier: revealTier(op.rarity),
              ...(result.extras > 0
                ? { note: `${result.extras} extra from the build-up!` }
                : {}),
            },
          ])
        }
      } else {
        // The endpoints each perform one operation, so a quantity is that many
        // sequential calls rather than a bulk request the server does not offer.
        let succeeded = 0
        for (let i = 0; i < repeats; i += 1) {
          const ok =
            op.kind === 'merge'
              ? await mergeUp(op.element, op.rarity)
              : await combine(op.a, op.b, op.rarity)
          if (!ok) break
          succeeded += 1
        }
        if (succeeded > 0) {
          reveal.show([
            op.kind === 'merge'
              ? {
                  image: collectableIcon(op.element, op.to),
                  title: `${label(op.to)} ${label(op.element)}`,
                  tier: revealTier(op.to),
                  note: 'merged',
                  ...(succeeded > 1 ? { amount: `×${succeeded}` } : {}),
                }
              : {
                  image: collectableIcon(op.result, op.rarity),
                  title: `${label(op.rarity)} ${label(op.result)}`,
                  tier: revealTier(op.rarity),
                  note: 'combined',
                  ...(succeeded > 1 ? { amount: `×${succeeded}` } : {}),
                },
          ])
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
        {held.length === 0 && dropped.length === 0 && opened.length === 0 ? (
          <p className="empty">Nothing yet. Log something you did and the elements start arriving.</p>
        ) : null}

        {held.length > 0 && (
          <>
            <div className="label">Collectables</div>
            <div className="hoard-grid">
              {held.map(({ element, rarity, count }) => {
                const icon = collectableIcon(element, rarity)
                const tier = revealTier(rarity)
                return (
                  <button
                    type="button"
                    key={stockKey(element, rarity)}
                    className={tileClass('item', tier)}
                    draggable
                    onDragStart={(event) =>
                      event.dataTransfer.setData(
                        'text/plain',
                        dragPayload({ type: 'collectable', element, rarity }),
                      )
                    }
                    // data-name drives the hover tooltip, which is CSS-only and
                    // therefore invisible to assistive tech; the label is what
                    // actually names the control.
                    data-name={`${label(element)} ${label(rarity)}`}
                    aria-label={`${label(element)} ${label(rarity)}, ${count} held`}
                    onClick={() => addToBench({ type: 'collectable', element, rarity })}
                    onDoubleClick={() => setInspected({ type: 'collectable', element, rarity })}
                  >
                    <img src={icon} width={50} height={50} alt="" />
                    {tier && <TileSheen icon={icon} />}
                    <span className="n">{count}</span>
                  </button>
                )
              })}
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
                const icon = receptacleIcon(receptacle.virtue, receptacle.rarity)
                const tier = revealTier(receptacle.rarity)
                return (
                  <button
                    type="button"
                    key={receptacle.id}
                    className={tileClass(hasKey ? 'item' : 'item locked', tier)}
                    draggable
                    onDragStart={(event) =>
                      event.dataTransfer.setData(
                        'text/plain',
                        dragPayload({ type: 'receptacle', receptacle }),
                      )
                    }
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
                    <img src={icon} width={50} height={50} alt="" />
                    {tier && <TileSheen icon={icon} />}
                  </button>
                )
              })}
            </div>
          </>
        )}

        {opened.length > 0 && (
          <>
            <div className="label">Receptacles — opened</div>
            <div className="opened-list">
              {opened.map((receptacle) => (
                <button
                  type="button"
                  key={receptacle.id}
                  className="opened-row"
                  onClick={() => setInspected({ type: 'receptacle', receptacle })}
                >
                  <img
                    src={receptacleIcon(receptacle.virtue, receptacle.rarity)}
                    width={40}
                    height={40}
                    alt=""
                  />
                  <div className="opened-info">
                    <div className="opened-title">
                      {label(receptacle.rarity)} of {label(receptacle.virtue)}
                    </div>
                    <div className="opened-text">
                      {receptacle.reward_text ?? receptacle.content?.text ?? '—'}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="panel bench">
        <div
          className={dragOver ? 'slots drag-over' : 'slots'}
          onDragOver={(event) => {
            event.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={dropOnBench}
        >
          {bench.length === 0 ? (
            <span className="placeholder">
              Drag items in (or click) · double-click to inspect
            </span>
          ) : (
            bench.map((item, index) => {
              const icon =
                item.type === 'collectable'
                  ? collectableIcon(item.element, item.rarity)
                  : receptacleIcon(item.receptacle.virtue, item.receptacle.rarity)
              const tier = revealTier(
                item.type === 'collectable' ? item.rarity : item.receptacle.rarity,
              )
              return (
                <button
                  type="button"
                  className={tileClass('item', tier)}
                  key={index}
                  title="Take it back off"
                  onClick={() => setBench((c) => c.filter((_, i) => i !== index))}
                >
                  <img src={icon} width={44} height={44} alt="" />
                  {tier && <TileSheen icon={icon} />}
                </button>
              )
            })
          )}
        </div>

        {soleCollectable ? (
          <>
            {soleHeld > 1 && (
              <input
                className="qty"
                type="number"
                min={1}
                max={soleHeld}
                value={sellQuantity}
                aria-label={`How many to sell (up to ${soleHeld})`}
                onChange={(event) => setSellQuantity(Number(event.target.value) || 1)}
              />
            )}
            <button
              type="button"
              className="btn-ghost sell-btn"
              disabled={busy}
              onClick={() => void runSell()}
            >
              {busy
                ? 'Selling…'
                : `Sell${sellCount > 1 ? ` ×${sellCount}` : ''} for ${
                    sellPrice(soleCollectable.element, soleCollectable.rarity) * sellCount
                  }`}
            </button>
          </>
        ) : (
          <>
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
          </>
        )}

        <RecipeInfo />
      </div>

      {/* A blocked bench says why, rather than leaving a dead button. Not shown
          in sell mode, where a lone item is deliberate rather than a mistake. */}
      {op.kind === 'blocked' && bench.length > 0 && !soleCollectable && (
        <p className="bench-reason">{op.reason}</p>
      )}

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
  const [qty, setQty] = useState(1)

  if (inspected.type === 'receptacle') {
    const { receptacle } = inspected

    if (receptacle.state === 'OPENED') {
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
            <div className="label">
              opened{receptacle.value !== null ? ` · was worth ${receptacle.value}` : ''}
            </div>
            <p className="desc">
              {receptacle.reward_text ?? receptacle.content?.text ?? 'Nothing recorded.'}
            </p>
            <p className="legend">{receptacleFlavor(receptacle.virtue, receptacle.rarity)}</p>
            <div className="detail-actions">
              <button type="button" className="btn-ghost" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        </Modal>
      )
    }

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
          <p className="legend">{receptacleFlavor(receptacle.virtue, receptacle.rarity)}</p>
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
  const sellCount = Math.max(1, Math.min(qty, Math.max(count, 1)))

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
        <p className="legend">{collectableFlavor(element, rarity)}</p>
        <div className="detail-actions">
          {count > 1 && (
            <input
              className="qty"
              type="number"
              min={1}
              max={count}
              value={qty}
              aria-label={`How many to sell (up to ${count})`}
              onChange={(event) => setQty(Number(event.target.value) || 1)}
            />
          )}
          <button
            type="button"
            className="btn-ghost"
            disabled={count < 1}
            onClick={() => {
              void sell(element, rarity, sellCount)
              onClose()
            }}
          >
            Sell {sellCount > 1 ? `×${sellCount}` : 'one'} for {price * sellCount}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </Modal>
  )
}
