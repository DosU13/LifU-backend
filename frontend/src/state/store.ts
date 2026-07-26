import { create } from 'zustand'

import { api, ApiError } from '../api'
import type { BuyResult, GameState, OpenResult, Receptacle, Stocks, Treasure } from '../types'

export interface GameStore {
  // Server state. `null` until the first hydrate succeeds.
  coins: number
  stocks: Stocks
  treasures: Treasure[]
  droppedReceptacles: Receptacle[]
  stats: GameState['stats'] | null

  loading: boolean
  error: string | null
  hydrated: boolean

  hydrate: () => Promise<void>
  reset: () => void

  // Mutating calls return only what they changed; these apply that delta
  // rather than refetching the whole world.
  patchCoins: (coins: number) => void
  patchStocks: (stocks: Stocks) => void
  applyBuyResult: (result: BuyResult) => void
  applyOpenResult: (result: OpenResult) => void
  refreshTreasures: () => Promise<void>
}

const emptyState = {
  coins: 0,
  stocks: {} as Stocks,
  treasures: [] as Treasure[],
  droppedReceptacles: [] as Receptacle[],
  stats: null,
  loading: false,
  error: null,
  hydrated: false,
}

export const useGameStore = create<GameStore>((set, get) => ({
  ...emptyState,

  hydrate: async () => {
    set({ loading: true, error: null })
    try {
      const state = await api.state()
      set({
        coins: state.coins,
        stocks: state.stocks,
        treasures: state.treasures,
        droppedReceptacles: state.dropped_receptacles,
        stats: state.stats,
        hydrated: true,
        loading: false,
      })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof ApiError ? error.message : 'Could not load the game.',
      })
    }
  },

  reset: () => set({ ...emptyState }),

  patchCoins: (coins) => set({ coins }),

  patchStocks: (stocks) => set({ stocks }),

  applyBuyResult: (result) => {
    const { droppedReceptacles } = get()
    set({
      coins: result.coins,
      droppedReceptacles: [result.drop, ...droppedReceptacles],
    })
  },

  applyOpenResult: (result) => {
    const { droppedReceptacles } = get()
    set({
      coins: result.coins,
      // The receptacle is opened, so it leaves the "waiting to open" list.
      droppedReceptacles: droppedReceptacles.filter((r) => r.id !== result.receptacle.id),
    })
  },

  refreshTreasures: async () => {
    try {
      const { treasures } = await api.treasures()
      set({ treasures })
    } catch (error) {
      set({ error: error instanceof ApiError ? error.message : 'Could not load treasures.' })
    }
  },
}))
