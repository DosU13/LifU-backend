import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Reveal } from '../ui/Overlay'
import type { Prize } from '../ui/Overlay'

const ICON = '/icons/collectables/wind_core.png'

function show(tier?: Prize['tier']) {
  const { container } = render(
    <Reveal
      queue={[{ image: ICON, title: 'Sanctum of Freedom', tier }]}
      index={0}
      onAdvance={() => {}}
      onSkip={() => {}}
    />,
  )
  return container
}

describe('Reveal — rarity tiers', () => {
  it('leaves an untiered payout exactly as it was', () => {
    const container = show()

    expect(container.querySelector('.veil')).toBeInTheDocument()
    expect(container.querySelector('[class*="tier-"]')).toBeNull()
    for (const decoration of ['.sheen', '.motes', '.shock', '.flash', '.embers']) {
      expect(container.querySelector(decoration)).toBeNull()
    }
    // The plain reveal keeps its one set of rays.
    expect(container.querySelectorAll('.rays')).toHaveLength(1)
  })

  it('gilded shimmers and orbits, but does not disturb the screen', () => {
    const container = show('gilded')

    expect(container.querySelector('.veil.tier-gilded')).toBeInTheDocument()
    expect(container.querySelector('.sheen')).toBeInTheDocument()
    expect(container.querySelectorAll('.motes i')).toHaveLength(6)
    expect(container.querySelectorAll('.rays')).toHaveLength(1)
    for (const louder of ['.shock', '.flash', '.embers']) {
      expect(container.querySelector(louder)).toBeNull()
    }
  })

  it('radiant adds the counter-rotation and the shockwave, still no screen effects', () => {
    const container = show('radiant')

    expect(container.querySelector('.veil.tier-radiant')).toBeInTheDocument()
    expect(container.querySelectorAll('.rays')).toHaveLength(2)
    expect(container.querySelector('.rays.violet')).toBeInTheDocument()
    expect(container.querySelector('.shock')).toBeInTheDocument()
    expect(container.querySelectorAll('.motes i')).toHaveLength(10)
    expect(container.querySelector('.flash')).toBeNull()
    expect(container.querySelector('.embers')).toBeNull()
  })

  it('mythic is the only one the whole screen reacts to', () => {
    const container = show('mythic')

    expect(container.querySelector('.veil.tier-mythic')).toBeInTheDocument()
    expect(container.querySelector('.flash')).toBeInTheDocument()
    expect(container.querySelectorAll('.embers i')).toHaveLength(18)
    // Everything the quieter tiers earned comes with it.
    expect(container.querySelector('.sheen')).toBeInTheDocument()
    expect(container.querySelector('.shock')).toBeInTheDocument()
    expect(container.querySelectorAll('.motes i')).toHaveLength(14)
  })

  it('masks the shimmer with the icon so it follows the silhouette', () => {
    const sheen = show('gilded').querySelector<HTMLElement>('.sheen')

    expect(sheen?.style.maskImage || sheen?.style.getPropertyValue('-webkit-mask-image')).toContain(
      ICON,
    )
  })

  it('keeps all of it out of the accessibility tree', () => {
    // None of this says anything the title underneath does not.
    const container = show('mythic')

    for (const decoration of ['.rays', '.flash', '.embers', '.sheen', '.shock', '.motes']) {
      for (const element of container.querySelectorAll(decoration)) {
        expect(element).toHaveAttribute('aria-hidden', 'true')
      }
    }
  })
})
