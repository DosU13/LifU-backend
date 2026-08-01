import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { useGameStore } from '../state/store'
import type { BuyResult, GameState, OpenResult, Receptacle } from '../types'

function receptacle(id: string, overrides: Partial<Receptacle> = {}): Receptacle {
  return {
    id,
    state: 'DROPPED',
    virtue: 'SERENITY',
    rarity: 'CHEST',
    is_generated: false,
    is_secret: false,
    friend_name: null,
    created_at: '2026-01-01T00:00:00Z',
    opened_at: null,
    key_needed: { element: 'OCEAN', rarity: 'CRYSTAL' },
    // DROPPED means unopened, and the server sends nothing about the contents
    // until it is opened. Override these only on an OPENED fixture.
    value: null,
    reward_text: null,
    content: null,
    ...overrides,
  }
}

const serverState: GameState = {
  coins: 120,
  stocks: { FIRE_FRAGMENT: 3, OCEAN_CRYSTAL: 1 },
  treasures: [{ id: 't1', slot: 0, price: 30, pity: { VAULT: 2, SANCTUM: 5 }, contents: [] }],
  dropped_receptacles: [receptacle('r1')],
  stats: { per_day: { '2026-01-01': 2 }, virtue_means: {} as never, streak: 3 },
}

beforeEach(() => {
  useGameStore.getState().reset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('hydrate', () => {
  it('loads the whole world from the server snapshot', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)

    await useGameStore.getState().hydrate()

    const state = useGameStore.getState()
    expect(state.coins).toBe(120)
    expect(state.stocks.FIRE_FRAGMENT).toBe(3)
    expect(state.treasures).toHaveLength(1)
    expect(state.droppedReceptacles).toHaveLength(1)
    expect(state.stats?.streak).toBe(3)
    expect(state.hydrated).toBe(true)
    expect(state.loading).toBe(false)
  })

  it('surfaces a failure without marking the world hydrated', async () => {
    vi.spyOn(api, 'state').mockRejectedValue(new Error('offline'))

    await useGameStore.getState().hydrate()

    const state = useGameStore.getState()
    expect(state.hydrated).toBe(false)
    expect(state.error).toBeTruthy()
    expect(state.loading).toBe(false)
  })
})

describe('delta patching', () => {
  it('patches coins and stocks without touching anything else', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)
    await useGameStore.getState().hydrate()

    useGameStore.getState().patchCoins(500)
    useGameStore.getState().patchStocks({ FIRE_SHARD: 1 })

    const state = useGameStore.getState()
    expect(state.coins).toBe(500)
    expect(state.stocks).toEqual({ FIRE_SHARD: 1 })
    expect(state.treasures).toHaveLength(1) // untouched
  })

  it('a buy adds the drop and updates coins', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)
    await useGameStore.getState().hydrate()

    const result: BuyResult = {
      drop: receptacle('r2'),
      dropped_rarity: 'CHEST',
      was_pity: false,
      price_paid: 30,
      coins: 90,
      pity: { VAULT: 3, SANCTUM: 6 },
      treasure_gone: false,
    }
    useGameStore.getState().applyBuyResult(result)

    const state = useGameStore.getState()
    expect(state.coins).toBe(90)
    expect(state.droppedReceptacles.map((r) => r.id)).toEqual(['r2', 'r1'])
  })

  it('an open removes the receptacle from the waiting list and credits coins', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)
    await useGameStore.getState().hydrate()

    const result: OpenResult = {
      receptacle: receptacle('r1', { state: 'OPENED', opened_at: '2026-01-02T00:00:00Z' }),
      coins_gained: 20,
      coins: 140,
    }
    useGameStore.getState().applyOpenResult(result)

    const state = useGameStore.getState()
    expect(state.coins).toBe(140)
    expect(state.droppedReceptacles).toHaveLength(0)
  })

  it('refreshTreasures replaces only the treasure list', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)
    await useGameStore.getState().hydrate()
    vi.spyOn(api, 'treasures').mockResolvedValue({
      treasures: [{ id: 't9', slot: 1, price: 5, pity: {}, contents: [] }],
    })

    await useGameStore.getState().refreshTreasures()

    const state = useGameStore.getState()
    expect(state.treasures.map((t) => t.id)).toEqual(['t9'])
    expect(state.coins).toBe(120) // untouched
  })
})

describe('reset', () => {
  it('clears the world on sign out', async () => {
    vi.spyOn(api, 'state').mockResolvedValue(serverState)
    await useGameStore.getState().hydrate()

    useGameStore.getState().reset()

    const state = useGameStore.getState()
    expect(state.coins).toBe(0)
    expect(state.droppedReceptacles).toHaveLength(0)
    expect(state.hydrated).toBe(false)
  })
})
