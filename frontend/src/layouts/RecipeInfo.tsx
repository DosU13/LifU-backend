import { useEffect, useRef, useState } from 'react'

import { COLLECTABLE_RARITIES } from '../types'
import { COMBINED_PAIRS, label } from '../domain'
import { collectableIcon } from '../ui/Icon'

const BASE = ['SPACE', 'AIR', 'FIRE', 'WATER', 'EARTH'] as const

/**
 * The little (i) beside the merge button.
 *
 * The three recipes are not discoverable by poking at the bench — especially
 * the ten combine pairs, which are otherwise pure memorisation.
 */
export function RecipeInfo() {
  const [open, setOpen] = useState(false)
  const wrapper = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    function onPointerDown(event: MouseEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="info-wrap" ref={wrapper}>
      <button
        type="button"
        className={open ? 'info-btn on' : 'info-btn'}
        aria-expanded={open}
        aria-label="What merges into what"
        onClick={() => setOpen((v) => !v)}
      >
        i
      </button>

      {open && (
        <div className="info-pop" role="dialog" aria-label="Recipes">
          <h3>Merge up</h3>
          <p>Three of the same element and rarity become one of the next rarity.</p>
          <div className="ladder">
            {COLLECTABLE_RARITIES.map((rarity, index) => (
              <span key={rarity}>
                {index > 0 && <span className="arrow">→</span>}
                <b>{label(rarity)}</b>
              </span>
            ))}
          </div>

          <h3>Harmony merge</h3>
          <p>
            One of each of the five base elements, all the same rarity, becomes five
            Harmony — then keeps rolling for extras until it fails.
          </p>
          <div className="recipe-row">
            {BASE.map((element) => (
              <img
                key={element}
                src={collectableIcon(element, 'FRAGMENT')}
                width={22}
                height={22}
                alt={label(element)}
              />
            ))}
            <span className="arrow">→</span>
            <img src={collectableIcon('HARMONY', 'FRAGMENT')} width={22} height={22} alt="" />
            <span>×5+</span>
          </div>

          <h3>Combine</h3>
          <p>
            Two base elements plus one Harmony, all the same rarity, become one combined
            element — the keys receptacles open with.
          </p>
          <div className="pairs">
            {COMBINED_PAIRS.map(({ a, b, result }) => (
              <div className="recipe-row" key={result}>
                <img src={collectableIcon(a, 'FRAGMENT')} width={20} height={20} alt="" />
                <span>+</span>
                <img src={collectableIcon(b, 'FRAGMENT')} width={20} height={20} alt="" />
                <span className="arrow">→</span>
                <img src={collectableIcon(result, 'FRAGMENT')} width={20} height={20} alt="" />
                <span>{label(result)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
