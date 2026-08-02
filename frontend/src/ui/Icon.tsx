import type { CollectableRarity, Element, ReceptacleRarity, Virtue } from '../types'
import { label } from '../domain'

/**
 * The 156 generated icons, addressed the same way the backend keys its stock.
 *
 * `serialize_stocks` emits "FIRE_SHARD", and the icon files are named
 * `fire_shard.png`, so a stock key maps to a file by lowercasing it. That is
 * deliberate: it means adding an element never requires editing a lookup table
 * here, and a missing icon shows up as a broken image rather than silently
 * rendering the wrong art.
 */

const COLLECTABLES = '/icons/collectables'
const RECEPTACLES = '/icons/receptacles'

export function collectableIcon(element: Element, rarity: CollectableRarity): string {
  return `${COLLECTABLES}/${element.toLowerCase()}_${rarity.toLowerCase()}.png`
}

export function receptacleIcon(virtue: Virtue, rarity: ReceptacleRarity): string {
  return `${RECEPTACLES}/${virtue.toLowerCase()}_${rarity.toLowerCase()}.png`
}

/** The one dedicated treasure-chest icon — a slot isn't any one virtue or
 * rarity until you buy it, so it never borrows receptacle art. */
export function treasureIcon(): string {
  return '/icons/misc/treasure_chest.png'
}

/** From a backend stock key such as "FIRE_SHARD". */
export function iconForStockKey(key: string): string {
  return `${COLLECTABLES}/${key.toLowerCase()}.png`
}

type Size = 'sm' | 'md' | 'lg' | 'xl'

const SIZES: Record<Size, number> = { sm: 22, md: 50, lg: 96, xl: 190 }

interface CollectableIconProps {
  element: Element
  rarity: CollectableRarity
  size?: Size
  className?: string
}

export function CollectableIcon({
  element,
  rarity,
  size = 'md',
  className,
}: CollectableIconProps) {
  const px = SIZES[size]
  return (
    <img
      src={collectableIcon(element, rarity)}
      width={px}
      height={px}
      className={className}
      // Decorative wherever a visible label sits beside it; callers that show
      // an icon alone pass their own alt through a wrapper.
      alt={`${label(element)} ${label(rarity)}`}
      draggable={false}
    />
  )
}

interface ReceptacleIconProps {
  virtue: Virtue
  rarity: ReceptacleRarity
  size?: Size
  className?: string
}

export function ReceptacleIcon({
  virtue,
  rarity,
  size = 'md',
  className,
}: ReceptacleIconProps) {
  const px = SIZES[size]
  return (
    <img
      src={receptacleIcon(virtue, rarity)}
      width={px}
      height={px}
      className={className}
      alt={`${label(rarity)} of ${label(virtue)}`}
      draggable={false}
    />
  )
}
