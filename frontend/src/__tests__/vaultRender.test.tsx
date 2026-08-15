import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { Vault } from '../layouts/Vault'
import { useGameStore } from '../state/store'
import { stockKey } from '../types'
import type { GeneratedContent, Receptacle } from '../types'

function receptacle(overrides: Partial<Receptacle> = {}): Receptacle {
  return {
    id: 'r1',
    state: 'DROPPED',
    virtue: 'SERENITY',
    rarity: 'SAFE',
    is_generated: false,
    is_secret: false,
    friend_name: null,
    created_at: '2026-01-01T00:00:00Z',
    opened_at: null,
    key_needed: { element: 'OCEAN', rarity: 'ESSENCE' },
    value: null,
    reward_text: null,
    content: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useGameStore.setState({ stocks: {}, droppedReceptacles: [], events: [] })
})

describe('the hoard', () => {
  it('says something useful when it is empty', () => {
    render(<Vault />)
    expect(screen.getByText(/nothing yet/i)).toBeInTheDocument()
  })

  it('shows only what is actually held', () => {
    useGameStore.setState({
      stocks: {
        [stockKey('FIRE', 'FRAGMENT')]: 12,
        [stockKey('WATER', 'FRAGMENT')]: 0,
      },
    })
    render(<Vault />)

    expect(screen.getByText('12')).toBeInTheDocument()
    // A zero counter is absence, not an entry showing "0".
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })
})

describe('rarity in the grid', () => {
  const tile = (name: RegExp) => screen.getByRole('button', { name })

  function withOneOfEach() {
    useGameStore.setState({
      stocks: {
        [stockKey('FIRE', 'FRAGMENT')]: 3,
        [stockKey('FIRE', 'ESSENCE')]: 3,
        [stockKey('FIRE', 'SOUL')]: 3,
        [stockKey('FIRE', 'CORE')]: 3,
      },
    })
    render(<Vault />)
  }

  it('dresses only the top three rarities', () => {
    withOneOfEach()

    expect(tile(/fire fragment, 3 held/i).className).toBe('item')
    expect(tile(/fire essence, 3 held/i)).toHaveClass('tier-gilded')
    expect(tile(/fire soul, 3 held/i)).toHaveClass('tier-radiant')
    expect(tile(/fire core, 3 held/i)).toHaveClass('tier-mythic')
  })

  it('only pays for a shimmer on the tiles that use one', () => {
    // Ninety-odd tiles can fit in the hoard; an idle node on each is the cost
    // this is avoiding.
    withOneOfEach()

    expect(tile(/fire fragment, 3 held/i).querySelector('.tile-sheen')).toBeNull()
    expect(tile(/fire core, 3 held/i).querySelector('.tile-sheen')).toBeInTheDocument()
  })

  it('masks each shimmer with that tile own icon', () => {
    withOneOfEach()
    const sheen = tile(/fire core, 3 held/i).querySelector<HTMLElement>('.tile-sheen')

    expect(sheen?.style.maskImage).toContain('fire_core.png')
    expect(sheen).toHaveAttribute('aria-hidden', 'true')
  })

  it('reaches sealed receptacles too, without disturbing the locked state', () => {
    useGameStore.setState({
      stocks: {},
      droppedReceptacles: [receptacle({ rarity: 'SANCTUM', virtue: 'FREEDOM' })],
    })
    render(<Vault />)

    const sealed = screen.getByRole('button', { name: /sanctum of freedom, locked/i })
    expect(sealed).toHaveClass('locked')
    expect(sealed).toHaveClass('tier-mythic')
  })
})

describe('receptacle key badges', () => {
  it('marks a receptacle ready when its key is held', () => {
    useGameStore.setState({
      stocks: { [stockKey('OCEAN', 'ESSENCE')]: 1 },
      droppedReceptacles: [receptacle()],
    })
    render(<Vault />)

    const item = screen.getByRole('button', { name: /safe of serenity/i })
    expect(item).not.toHaveClass('locked')
  })

  it('marks it locked without the key', () => {
    useGameStore.setState({ stocks: {}, droppedReceptacles: [receptacle()] })
    render(<Vault />)

    expect(screen.getByRole('button', { name: /safe of serenity/i })).toHaveClass('locked')
  })

  it('derives the key from virtue and rarity, not from the server field', () => {
    // Sanctum of Freedom ⇒ Wind Core. Holding it unlocks; holding the wrong
    // key does not.
    useGameStore.setState({
      stocks: { [stockKey('WIND', 'CORE')]: 1 },
      droppedReceptacles: [receptacle({ virtue: 'FREEDOM', rarity: 'SANCTUM' })],
    })
    render(<Vault />)

    expect(screen.getByRole('button', { name: /sanctum of freedom/i })).not.toHaveClass(
      'locked',
    )
  })
})

describe('the bench', () => {
  it('names the operation once the pieces are in', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'FRAGMENT')]: 9 } })
    render(<Vault />)

    const fire = screen.getByRole('button', { name: /fire fragment/i })
    await userEvent.click(fire)
    await userEvent.click(fire)
    await userEvent.click(fire)

    expect(screen.getByRole('button', { name: /merge up → fire shard/i })).toBeEnabled()
  })

  it('explains a blocked bench rather than leaving a dead button', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'FRAGMENT')]: 9 } })
    render(<Vault />)

    // Two of a kind can't merge (needs three) and isn't a lone item either —
    // that's the case that should still explain itself.
    const fire = screen.getByRole('button', { name: /fire fragment/i })
    await userEvent.click(fire)
    await userEvent.click(fire)

    expect(screen.getByText(/three of the same/i)).toBeInTheDocument()
  })

  it('offers to sell an exact count when only one item is on the bench', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'FRAGMENT')]: 9 } })
    render(<Vault />)

    await userEvent.click(screen.getByRole('button', { name: /fire fragment/i }))

    expect(screen.getByRole('button', { name: /sell for 1/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/how many to sell \(up to 9\)/i)).toBeInTheDocument()
  })

  it('offers a quantity only when more than one run is possible', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'FRAGMENT')]: 9 } })
    render(<Vault />)

    const fire = screen.getByRole('button', { name: /fire fragment/i })
    await userEvent.click(fire)
    await userEvent.click(fire)
    await userEvent.click(fire)

    // 9 held / 3 per merge = 3 possible runs.
    expect(screen.getByLabelText(/how many times \(up to 3\)/i)).toBeInTheDocument()
  })

  it('hides the quantity when only one run is possible', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'FRAGMENT')]: 3 } })
    render(<Vault />)

    const fire = screen.getByRole('button', { name: /fire fragment/i })
    await userEvent.click(fire)
    await userEvent.click(fire)
    await userEvent.click(fire)

    expect(screen.queryByLabelText(/how many times/i)).not.toBeInTheDocument()
  })

  it('refuses to open a receptacle without its key', async () => {
    useGameStore.setState({ stocks: {}, droppedReceptacles: [receptacle()] })
    render(<Vault />)

    await userEvent.click(screen.getByRole('button', { name: /safe of serenity/i }))

    // Disabled locally, so a keyless open never becomes a 400 round trip.
    expect(screen.getByRole('button', { name: /no key/i })).toBeDisabled()
    expect(screen.getByText(/needs one ocean essence/i)).toBeInTheDocument()
  })
})

describe('inspecting an item', () => {
  it('shows what a collectable merges into and what it sells for', async () => {
    useGameStore.setState({ stocks: { [stockKey('FIRE', 'SHARD')]: 4 } })
    render(<Vault />)

    await userEvent.dblClick(screen.getByRole('button', { name: /fire shard/i }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/three of these merge into one fire crystal/i)).toBeInTheDocument()
    // base element at SHARD: 1 * 3^1
    expect(within(dialog).getByText(/4 held · sells for 3/i)).toBeInTheDocument()
  })

  it('never reveals what is inside an unopened receptacle', async () => {
    useGameStore.setState({
      stocks: { [stockKey('OCEAN', 'ESSENCE')]: 1 },
      droppedReceptacles: [receptacle()],
    })
    render(<Vault />)

    await userEvent.dblClick(screen.getByRole('button', { name: /safe of serenity/i }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/stays hidden until it opens/i)).toBeInTheDocument()
    expect(within(dialog).getByText(/ready — one ocean essence/i)).toBeInTheDocument()
  })
})

describe('opened receptacles', () => {
  function generated(overrides: Partial<GeneratedContent> = {}): GeneratedContent {
    return {
      kind: 'QUOTE',
      title: 'A thought',
      url: '',
      author: 'Marcus Aurelius',
      text: 'The obstacle is the way.',
      ...overrides,
    }
  }

  function opened(overrides: Partial<Receptacle> = {}): Receptacle {
    return receptacle({
      id: 'o1',
      state: 'OPENED',
      opened_at: '2026-01-02T00:00:00Z',
      value: 40,
      content: generated(),
      ...overrides,
    })
  }

  it('a click replays the full tiered reveal it got the first time', async () => {
    vi.spyOn(api, 'listReceptacles').mockResolvedValue({ receptacles: [opened()] })
    render(<Vault />)

    await userEvent.click(await screen.findByRole('button', { name: /safe of serenity/i }))

    const frame = document.querySelector('.prize-frame')
    expect(frame).toBeInTheDocument()
    expect(document.querySelector('.veil.tier-gilded')).toBeInTheDocument()
    // Scoped to the reveal — the same text also legitimately sits in the
    // row's own preview caption underneath. Same rich-content path a fresh
    // open uses: the quote itself, not a caption.
    expect(within(frame as HTMLElement).getByText('The obstacle is the way.')).toBeInTheDocument()
    expect(within(frame as HTMLElement).getByText('Marcus Aurelius')).toBeInTheDocument()
  })

  it('falls back to the hand-written reward text when there is no generated content', async () => {
    vi.spyOn(api, 'listReceptacles').mockResolvedValue({
      receptacles: [opened({ content: null, reward_text: 'Movie night, your pick.' })],
    })
    render(<Vault />)

    await userEvent.click(await screen.findByRole('button', { name: /safe of serenity/i }))

    // Scoped to the reveal itself — the same text also legitimately sits in
    // the row's own preview caption underneath, which is not what this is
    // testing for.
    const veil = document.querySelector('.veil')
    expect(veil).not.toBeNull()
    expect(within(veil as HTMLElement).getByText('Movie night, your pick.')).toBeInTheDocument()
  })
})
