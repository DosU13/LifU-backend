import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Treasury } from '../layouts/Treasury'
import { useGameStore } from '../state/store'
import type { Treasure } from '../types'

function treasure(overrides: Partial<Treasure> = {}): Treasure {
  return {
    id: 't1',
    slot: 0,
    price: 240,
    pity: { VAULT: 2, SANCTUM: 5 },
    contents: [
      { virtue: 'NURTURING', rarity: 'POUCH', is_secret: false, friend_name: null },
      { virtue: 'SERENITY', rarity: 'SAFE', is_secret: false, friend_name: null },
      { virtue: 'FREEDOM', rarity: 'SANCTUM', is_secret: false, friend_name: null },
    ],
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useGameStore.setState({
    treasures: [],
    coins: 0,
    selectedTreasureId: null,
    droppedReceptacles: [],
    events: [],
  })
})

describe('the treasure selectors', () => {
  it('says so when there are none', () => {
    render(<Treasury />)
    expect(screen.getByText(/no treasures right now/i)).toBeInTheDocument()
  })

  it("shows the server's fixed price, not one derived from the contents", () => {
    // Regression guard: price used to be recomputed from current contents, so
    // a treasure got cheaper as it emptied. It is fixed at generation now.
    useGameStore.setState({ treasures: [treasure({ price: 880 })], coins: 1000 })
    render(<Treasury />)

    expect(screen.getByRole('button', { name: /880 coins, 3 sealed/i })).toBeInTheDocument()
  })

  it('invites a selection before one is made', () => {
    useGameStore.setState({ treasures: [treasure()], coins: 1000 })
    render(<Treasury />)

    expect(screen.getByText(/pick a treasure/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^buy/i })).not.toBeInTheDocument()
  })

  it('lays the contents out once selected', async () => {
    useGameStore.setState({ treasures: [treasure()], coins: 1000 })
    render(<Treasury />)

    await userEvent.click(screen.getByRole('button', { name: /240 coins/i }))

    expect(screen.getByText('Sanctum of Freedom')).toBeInTheDocument()
    expect(screen.getByText('Safe of Serenity')).toBeInTheDocument()
    expect(screen.getByText('Pouch of Nurturing')).toBeInTheDocument()
  })
})

describe('rarity in the lineup', () => {
  const floater = (name: string) => screen.getByText(name).closest('.floater')

  async function selectIt() {
    useGameStore.setState({ treasures: [treasure()], coins: 1000 })
    render(<Treasury />)
    await userEvent.click(screen.getByRole('button', { name: /240 coins/i }))
  }

  it('marks the good ones and leaves the rest plain', async () => {
    await selectIt()

    expect(floater('Pouch of Nurturing')?.className).toBe('floater')
    expect(floater('Safe of Serenity')).toHaveClass('tier-gilded')
    expect(floater('Sanctum of Freedom')).toHaveClass('tier-mythic')
  })

  it('keeps the tier alongside the elimination states, not instead of them', async () => {
    // Both live in the same className; a tier that clobbered `.out` or `.won`
    // would break the buy animation rather than merely look wrong.
    await selectIt()
    expect(floater('Sanctum of Freedom')?.className).toBe('floater tier-mythic')
  })

  it('gives every tier the sheen, but only mythic the orbiting motes', async () => {
    await selectIt()

    expect(floater('Pouch of Nurturing')?.querySelector('.floater-sheen')).toBeNull()
    expect(floater('Safe of Serenity')?.querySelector('.floater-sheen')).toBeInTheDocument()
    expect(floater('Sanctum of Freedom')?.querySelector('.floater-sheen')).toBeInTheDocument()

    expect(floater('Safe of Serenity')?.querySelectorAll('.floater-motes i')).toHaveLength(0)
    expect(floater('Sanctum of Freedom')?.querySelectorAll('.floater-motes i')).toHaveLength(6)
  })

  it('masks each sheen with that item own icon, not a generic square', async () => {
    await selectIt()

    const sheen = floater('Sanctum of Freedom')?.querySelector<HTMLElement>('.floater-sheen')
    expect(sheen?.style.maskImage).toContain('freedom_sanctum.png')
  })

  it('holds back the one-shot crown ring until there is actually a winner', async () => {
    // The buy sequence is exercised in elimination.test.ts; here it is enough
    // that nothing claims to be a winner before a buy has even happened.
    await selectIt()
    expect(document.querySelector('.floater-shock')).toBeNull()
  })

  it('keeps every decoration out of the accessibility tree', async () => {
    await selectIt()

    const sanctum = floater('Sanctum of Freedom')
    for (const selector of ['.floater-sheen', '.floater-motes']) {
      expect(sanctum?.querySelector(selector)).toHaveAttribute('aria-hidden', 'true')
    }
  })
})

describe('buying', () => {
  it('is offered at the fixed price when affordable', async () => {
    useGameStore.setState({ treasures: [treasure()], coins: 500, selectedTreasureId: 't1' })
    render(<Treasury />)

    expect(screen.getByRole('button', { name: /buy — 240/i })).toBeEnabled()
  })

  it('is refused, with a reason, when the coins are not there', async () => {
    useGameStore.setState({ treasures: [treasure()], coins: 100, selectedTreasureId: 't1' })
    render(<Treasury />)

    expect(screen.getByRole('button', { name: /buy — 240/i })).toBeDisabled()
    expect(screen.getByText(/not enough coins/i)).toBeInTheDocument()
  })

  it('treats exactly the price as affordable', () => {
    useGameStore.setState({ treasures: [treasure()], coins: 240, selectedTreasureId: 't1' })
    render(<Treasury />)

    expect(screen.getByRole('button', { name: /buy — 240/i })).toBeEnabled()
  })

  it('offers letting a treasure go', () => {
    useGameStore.setState({ treasures: [treasure()], coins: 500, selectedTreasureId: 't1' })
    render(<Treasury />)

    expect(screen.getByRole('button', { name: /let it go/i })).toBeInTheDocument()
  })
})
