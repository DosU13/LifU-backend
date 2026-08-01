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
