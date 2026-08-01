import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { TreasurePanel } from '../components/TreasurePanel'
import { VaultPanel } from '../components/VaultPanel'
import { useGameStore } from '../state/store'
import type { BuyResult, Receptacle, Treasure } from '../types'
import { stockKey } from '../types'

function treasure(overrides: Partial<Treasure> = {}): Treasure {
  return {
    id: 't1',
    slot: 0,
    price: 25,
    pity: { VAULT: 5, SANCTUM: 40 },
    contents: [{ virtue: 'SERENITY', rarity: 'CHEST', is_secret: false, friend_name: null }],
    ...overrides,
  }
}

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
    // DROPPED means unopened, and the server sends nothing about the contents
    // until it is opened. Override these only on an OPENED fixture.
    value: null,
    reward_text: null,
    content: null,
    ...overrides,
  }
}

beforeEach(() => {
  useGameStore.getState().reset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fx queue', () => {
  it('a harmony merge queues exactly extras + 1 bursts', async () => {
    vi.spyOn(api, 'harmony').mockResolvedValue({ yield: 8, extras: 3, stocks: {} })

    await useGameStore.getState().mergeHarmony('FRAGMENT')

    const fx = useGameStore.getState().fx
    expect(fx).toHaveLength(1)
    expect(fx[0]).toMatchObject({ kind: 'harmony', bursts: 4 })
  })

  it('a harmony merge with no extras still queues one burst', async () => {
    vi.spyOn(api, 'harmony').mockResolvedValue({ yield: 5, extras: 0, stocks: {} })

    await useGameStore.getState().mergeHarmony('FRAGMENT')

    expect(useGameStore.getState().fx[0]).toMatchObject({ kind: 'harmony', bursts: 1 })
  })

  it('a buy queues a drop carrying the rarity that was actually won', async () => {
    useGameStore.setState({ treasures: [treasure({ slot: 2 })] })
    const result: BuyResult = {
      drop: receptacle({ id: 'r9' }),
      // The server reports what dropped even if recalculation relabels it.
      dropped_rarity: 'VAULT',
      was_pity: true,
      price_paid: 25,
      coins: 75,
      pity: { VAULT: 0, SANCTUM: 41 },
      treasure_gone: false,
    }
    vi.spyOn(api, 'buyTreasure').mockResolvedValue(result)
    vi.spyOn(api, 'treasures').mockResolvedValue({ treasures: [treasure({ slot: 2 })] })

    await useGameStore.getState().buyTreasure('t1')

    const fx = useGameStore.getState().fx
    expect(fx[0]).toMatchObject({ kind: 'drop', slot: 2, rarity: 'VAULT' })
    expect(useGameStore.getState().coins).toBe(75)
  })

  it('consumeFx removes only the finished effect', async () => {
    vi.spyOn(api, 'harmony').mockResolvedValue({ yield: 5, extras: 0, stocks: {} })
    await useGameStore.getState().mergeHarmony('FRAGMENT')
    await useGameStore.getState().mergeHarmony('FRAGMENT')

    const [first] = useGameStore.getState().fx
    useGameStore.getState().consumeFx(first!.id)

    const remaining = useGameStore.getState().fx
    expect(remaining).toHaveLength(1)
    expect(remaining[0]!.id).not.toBe(first!.id)
  })
})

describe('TreasurePanel', () => {
  it('invites you to hide a reward when there are no treasures', () => {
    render(<TreasurePanel />)
    expect(screen.getByText(/hide a reward/i)).toBeInTheDocument()
  })

  it('will not let you buy what you cannot afford', () => {
    useGameStore.setState({ treasures: [treasure({ price: 25 })], coins: 10 })
    render(<TreasurePanel />)

    expect(screen.getByRole('button', { name: /need ◈ 25/i })).toBeDisabled()
  })

  it('enables the buy once you have the coins', () => {
    useGameStore.setState({ treasures: [treasure({ price: 25 })], coins: 25 })
    render(<TreasurePanel />)

    expect(screen.getByRole('button', { name: /try it — ◈ 25/i })).toBeEnabled()
  })

  it('shows both pity counters against their thresholds', () => {
    useGameStore.setState({ treasures: [treasure()], coins: 100 })
    render(<TreasurePanel />)

    expect(screen.getByText('5/27')).toBeInTheDocument()
    expect(screen.getByText('40/81')).toBeInTheDocument()
  })

  it('never reveals what a treasure is worth inside', () => {
    useGameStore.setState({
      treasures: [
        treasure({
          contents: [
            { virtue: 'NURTURING', rarity: 'VAULT', is_secret: true, friend_name: 'alex' },
          ],
        }),
      ],
      coins: 100,
    })
    render(<TreasurePanel />)

    expect(screen.getByText(/vault of nurturing/i)).toBeInTheDocument()
    expect(screen.queryByText(/a nice dinner/i)).not.toBeInTheDocument()
  })
})

describe('VaultPanel', () => {
  it('says what to do when nothing has dropped', () => {
    render(<VaultPanel />)
    expect(screen.getByText(/try a treasure/i)).toBeInTheDocument()
  })

  it('blocks opening while you lack the key, and names what you need', () => {
    useGameStore.setState({ droppedReceptacles: [receptacle()], stocks: {} })
    render(<VaultPanel />)

    expect(screen.getByRole('button', { name: /open/i })).toBeDisabled()
    expect(screen.getByText(/ocean.*essence.*you have none/i)).toBeInTheDocument()
  })

  it('allows opening once the matching key is held', () => {
    useGameStore.setState({
      droppedReceptacles: [receptacle()],
      stocks: { [stockKey('OCEAN', 'ESSENCE')]: 2 },
    })
    render(<VaultPanel />)

    expect(screen.getByRole('button', { name: /open/i })).toBeEnabled()
    expect(screen.getByText(/you have 2/i)).toBeInTheDocument()
  })

  it('a key of the wrong rarity does not count', () => {
    useGameStore.setState({
      droppedReceptacles: [receptacle()],
      stocks: { [stockKey('OCEAN', 'CRYSTAL')]: 5 },
    })
    render(<VaultPanel />)

    expect(screen.getByRole('button', { name: /open/i })).toBeDisabled()
  })

  it('opening spends the key and clears the row', async () => {
    const user = userEvent.setup()
    useGameStore.setState({
      droppedReceptacles: [receptacle()],
      stocks: { [stockKey('OCEAN', 'ESSENCE')]: 1 },
    })
    vi.spyOn(api, 'openReceptacle').mockResolvedValue({
      receptacle: receptacle({ state: 'OPENED' }),
      coins_gained: 40,
      coins: 40,
    })
    vi.spyOn(api, 'collectables').mockResolvedValue({
      stocks: { [stockKey('OCEAN', 'ESSENCE')]: 0 },
      coins: 40,
    })
    render(<VaultPanel />)

    await user.click(screen.getByRole('button', { name: /open/i }))

    expect(useGameStore.getState().droppedReceptacles).toHaveLength(0)
    expect(useGameStore.getState().coins).toBe(40)
    expect(useGameStore.getState().fx.at(-1)).toMatchObject({ kind: 'open' })
  })
})
