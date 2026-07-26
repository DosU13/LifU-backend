import { create } from 'zustand'

import { api, ApiError } from '../api'
import type {
  BuyResult,
  CollectableRarity,
  Element,
  GameState,
  OpenResult,
  Receptacle,
  Stocks,
  Treasure,
} from '../types'

/** A one-line outcome to show the player after an action. */
export interface GameEvent {
  id: number
  kind: 'success' | 'error'
  message: string
}

export interface GameStore {
  coins: number
  stocks: Stocks
  treasures: Treasure[]
  droppedReceptacles: Receptacle[]
  stats: GameState['stats'] | null

  loading: boolean
  error: string | null
  hydrated: boolean
  events: GameEvent[]

  hydrate: () => Promise<void>
  reset: () => void
  dismissEvent: (id: number) => void

  // Deltas applied from mutating calls, instead of refetching the world.
  patchCoins: (coins: number) => void
  patchStocks: (stocks: Stocks) => void
  applyBuyResult: (result: BuyResult) => void
  applyOpenResult: (result: OpenResult) => void
  refreshTreasures: () => Promise<void>

  // Player actions. Each reports its own outcome and returns success.
  completeTask: (text: string) => Promise<boolean>
  submitReward: (text: string, isSecret: boolean, friendName?: string) => Promise<boolean>
  mergeUp: (element: Element, rarity: CollectableRarity) => Promise<boolean>
  mergeHarmony: (rarity: CollectableRarity) => Promise<boolean>
  combine: (a: Element, b: Element, rarity: CollectableRarity) => Promise<boolean>
  sell: (element: Element, rarity: CollectableRarity, count: number) => Promise<boolean>
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
  events: [] as GameEvent[],
}

let nextEventId = 1

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export const useGameStore = create<GameStore>((set, get) => {
  function report(kind: GameEvent['kind'], message: string) {
    const event = { id: nextEventId++, kind, message }
    set({ events: [...get().events, event].slice(-4) })
  }

  return {
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
        set({ loading: false, error: describe(error, 'Could not load the game.') })
      }
    },

    reset: () => set({ ...emptyState }),

    dismissEvent: (id) => set({ events: get().events.filter((e) => e.id !== id) }),

    patchCoins: (coins) => set({ coins }),

    patchStocks: (stocks) => set({ stocks }),

    applyBuyResult: (result) =>
      set({
        coins: result.coins,
        droppedReceptacles: [result.drop, ...get().droppedReceptacles],
      }),

    applyOpenResult: (result) =>
      set({
        coins: result.coins,
        droppedReceptacles: get().droppedReceptacles.filter(
          (r) => r.id !== result.receptacle.id,
        ),
      }),

    refreshTreasures: async () => {
      try {
        const { treasures } = await api.treasures()
        set({ treasures })
      } catch (error) {
        set({ error: describe(error, 'Could not load treasures.') })
      }
    },

    completeTask: async (text) => {
      try {
        const result = await api.completeTask(text)
        const awarded = Object.entries(result.fragments_awarded)
        // Fragments changed, and so did the stats/streak — refresh both.
        const [{ stocks }, stats] = await Promise.all([api.collectables(), api.stats()])
        set({ stocks, stats })
        report(
          'success',
          awarded.length === 0
            ? `Valued at ${result.task.value}. No fragments this time.`
            : `Valued at ${result.task.value} · ${awarded
                .map(([element, count]) => `${count} ${element.toLowerCase()}`)
                .join(', ')}`,
        )
        return true
      } catch (error) {
        report('error', describe(error, 'Could not save that task.'))
        return false
      }
    },

    submitReward: async (text, isSecret, friendName) => {
      try {
        const receptacle = await api.submitReward(text, isSecret, friendName)
        await get().refreshTreasures()
        report(
          'success',
          `Stored a ${receptacle.rarity.toLowerCase()} of ${receptacle.virtue.toLowerCase()}.`,
        )
        return true
      } catch (error) {
        report('error', describe(error, 'Could not store that reward.'))
        return false
      }
    },

    mergeUp: async (element, rarity) => {
      try {
        const { stocks } = await api.merge(element, rarity)
        set({ stocks })
        report('success', `Merged three ${element.toLowerCase()} ${rarity.toLowerCase()}s.`)
        return true
      } catch (error) {
        report('error', describe(error, 'Could not merge those.'))
        return false
      }
    },

    mergeHarmony: async (rarity) => {
      try {
        const result = await api.harmony(rarity)
        set({ stocks: result.stocks })
        report(
          'success',
          result.extras > 0
            ? `${result.yield} harmony — ${result.extras} extra from the build-up!`
            : `${result.yield} harmony.`,
        )
        return true
      } catch (error) {
        report('error', describe(error, 'Could not perform the harmony merge.'))
        return false
      }
    },

    combine: async (a, b, rarity) => {
      try {
        const result = await api.combine(a, b, rarity)
        set({ stocks: result.stocks })
        report('success', `Created a ${result.result_element.toLowerCase()} ${rarity.toLowerCase()}.`)
        return true
      } catch (error) {
        report('error', describe(error, 'Could not combine those.'))
        return false
      }
    },

    sell: async (element, rarity, count) => {
      try {
        const result = await api.sell(element, rarity, count)
        const gained = result.coins - get().coins
        set({ stocks: result.stocks, coins: result.coins })
        report('success', `Sold ${count} for ${gained} coins.`)
        return true
      } catch (error) {
        report('error', describe(error, 'Could not sell those.'))
        return false
      }
    },
  }
})
