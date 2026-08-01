import { create } from 'zustand'

import { api, ApiError } from '../api'
import type {
  BuyResult,
  CollectableRarity,
  Element,
  GameState,
  OpenResult,
  Receptacle,
  ReceptacleRarity,
  Stocks,
  TaskCompletion,
  Treasure,
} from '../types'

/** A one-line outcome to show the player after an action. */
export interface GameEvent {
  id: number
  kind: 'success' | 'error'
  message: string
}

/**
 * Something for the 3D scene to animate. Counts come from the server response
 * — the canvas replays what actually happened rather than rolling its own.
 */
export type FxPayload =
  | { kind: 'harmony'; bursts: number }
  | { kind: 'drop'; slot: number; rarity: ReceptacleRarity }
  | { kind: 'open' }

export type FxEvent = FxPayload & { id: number }

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
  fx: FxEvent[]
  selectedTreasureId: string | null

  hydrate: () => Promise<void>
  reset: () => void
  dismissEvent: (id: number) => void
  consumeFx: (id: number) => void
  selectTreasure: (id: string | null) => void

  // Deltas applied from mutating calls, instead of refetching the world.
  patchCoins: (coins: number) => void
  patchStocks: (stocks: Stocks) => void
  applyBuyResult: (result: BuyResult) => void
  applyOpenResult: (result: OpenResult) => void
  refreshTreasures: () => Promise<void>

  // Player actions. Each reports its own outcome and returns success.
  /** Resolves to the server's payout so the caller can replay it, or null on failure. */
  completeTask: (text: string) => Promise<TaskCompletion | null>
  submitReward: (text: string, isSecret: boolean, friendName?: string) => Promise<boolean>
  mergeUp: (element: Element, rarity: CollectableRarity) => Promise<boolean>
  mergeHarmony: (rarity: CollectableRarity) => Promise<boolean>
  combine: (a: Element, b: Element, rarity: CollectableRarity) => Promise<boolean>
  sell: (element: Element, rarity: CollectableRarity, count: number) => Promise<boolean>
  /** Resolves to the server's result so the caller can animate the real drop. */
  buyTreasure: (id: string) => Promise<BuyResult | null>
  discardTreasure: (id: string) => Promise<boolean>
  openReceptacle: (id: string) => Promise<boolean>
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
  fx: [] as FxEvent[],
  selectedTreasureId: null,
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

  function emitFx(payload: FxPayload) {
    set({ fx: [...get().fx, { ...payload, id: nextEventId++ }] })
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

    consumeFx: (id) => set({ fx: get().fx.filter((e) => e.id !== id) }),

    selectTreasure: (id) => set({ selectedTreasureId: id }),

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
        // Fragments changed, and so did the stats/streak — refresh both.
        const [{ stocks }, stats] = await Promise.all([api.collectables(), api.stats()])
        set({ stocks, stats })
        // The drops themselves are replayed by the caller's reveal, so this
        // only carries what the reveal does not show.
        report(
          'success',
          Object.keys(result.fragments_awarded).length === 0
            ? `Valued at ${result.task.value}. No fragments this time.`
            : `Valued at ${result.task.value}.`,
        )
        return result
      } catch (error) {
        report('error', describe(error, 'Could not save that task.'))
        return null
      }
    },

    submitReward: async (text, isSecret, friendName) => {
      try {
        await api.submitReward(text, isSecret, friendName)
        await get().refreshTreasures()
        // Deliberately vague: naming the receptacle here would give away which
        // one holds this reward, which is the whole thing being protected.
        report('success', 'Sealed away. You will find out which one when it opens.')
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
        // The base five plus however many extras the server actually rolled.
        emitFx({ kind: 'harmony', bursts: result.extras + 1 })
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

    buyTreasure: async (id) => {
      const slot = get().treasures.find((t) => t.id === id)?.slot ?? 0
      try {
        const result = await api.buyTreasure(id)
        get().applyBuyResult(result)
        emitFx({ kind: 'drop', slot, rarity: result.dropped_rarity })
        // Contents, price and pity all moved; and an emptied treasure was replaced.
        await get().refreshTreasures()
        if (result.treasure_gone) set({ selectedTreasureId: null })
        report(
          'success',
          result.was_pity
            ? `Pity paid out: a ${result.dropped_rarity.toLowerCase()}!`
            : `Bought for ${result.price_paid}.`,
        )
        return result
      } catch (error) {
        report('error', describe(error, 'Could not buy from that treasure.'))
        return null
      }
    },

    discardTreasure: async (id) => {
      try {
        await api.discardTreasure(id)
        set({ selectedTreasureId: null })
        // Its receptacles went back to the pool and a new treasure took the slot.
        await Promise.all([get().refreshTreasures(), get().hydrate()])
        report('success', 'Treasure let go. A new one takes its place.')
        return true
      } catch (error) {
        report('error', describe(error, 'Could not let that treasure go.'))
        return false
      }
    },

    openReceptacle: async (id) => {
      try {
        const result = await api.openReceptacle(id)
        get().applyOpenResult(result)
        emitFx({ kind: 'open' })
        // The key was spent.
        const { stocks } = await api.collectables()
        set({ stocks })
        report('success', `Opened — ${result.coins_gained} coins inside.`)
        return true
      } catch (error) {
        report('error', describe(error, 'Could not open that.'))
        return false
      }
    },
  }
})
