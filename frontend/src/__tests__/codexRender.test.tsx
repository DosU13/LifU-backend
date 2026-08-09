import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { Codex } from '../layouts/Codex'
import type { Task } from '../types'

function task(fragments: Partial<Record<string, number>>, createdAt: string): Task {
  return {
    id: Math.random().toString(36),
    text: 'did a thing',
    created_at: createdAt,
    value: 20,
    virtues: { AWARENESS: 0, CURIOSITY: 0, WILLPOWER: 0, COMPASSION: 0, DISCIPLINE: 0 },
    fragments_awarded: fragments,
  }
}

/** Codex.tsx checks matchMedia at mount to decide whether the leaf spins or
 * the spread swaps instantly — most navigation tests do not care which, so
 * they force the instant path to stay fast and avoid the timed animation. */
function mockPlainTurn(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  // matchMedia does not exist on this jsdom by default; leaving a mock
  // behind would leak the "instant swap" path into whichever test runs next.
  Reflect.deleteProperty(window, 'matchMedia')
})

describe('Codex — the book', () => {
  it('opens on the frontispiece', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    render(<Codex />)

    expect(await screen.findByText('The Codex of Elements')).toBeInTheDocument()
    expect(screen.getByText('The Three Qualities of Mind')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Previous' })).toBeDisabled()
  })

  it('walks forward and back between spreads, disabling at the ends', async () => {
    mockPlainTurn(true)
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    render(<Codex />)
    await screen.findByText('The Codex of Elements')

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('The Five Elements')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Previous' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Next →' })).toBeEnabled()

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('The Three Doshas')).toBeInTheDocument()
    // Two more spreads follow this one — Next must stay enabled here, not
    // disable early just because this used to be the last page in the book.
    expect(screen.getByRole('button', { name: 'Next →' })).toBeEnabled()

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('Beyond the Five')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next →' })).toBeEnabled()

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('Receptacles & Virtues')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next →' })).toBeDisabled()

    await fireEvent.click(screen.getByRole('button', { name: '← Previous' }))
    expect(screen.getByText('Beyond the Five')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: '← Previous' }))
    expect(screen.getByText('The Three Doshas')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: '← Previous' }))
    expect(screen.getByText('The Five Elements')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: '← Previous' }))
    expect(screen.getByText('The Codex of Elements')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Previous' })).toBeDisabled()
  })

  it('carries the ten combined elements, each naming its parent pair and virtue', async () => {
    mockPlainTurn(true)
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    render(<Codex />)
    await screen.findByText('The Codex of Elements')

    for (let i = 0; i < 3; i += 1) {
      await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    }
    // Substring matchers throughout: the real text is the gloss prefixed
    // with an em dash ("— Earth + Water"), so an exact-string query would
    // never match.
    expect(screen.getByText(/Earth \+ Water/)).toBeInTheDocument()
    expect(screen.getByText(/unlocks nurturing's receptacles/i)).toBeInTheDocument()
    expect(screen.getByText(/all five, at once/)).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText(/Air \+ Space/)).toBeInTheDocument()
    expect(screen.getByText(/unlocks freedom's receptacles/i)).toBeInTheDocument()
  })

  it("reads a constitution from every task logged, not what's currently held", async () => {
    // Deliberately not the day's fragments awarded pattern from Ledger — this
    // is exercising the reading, not the earning.
    const today = new Date().toISOString()
    vi.spyOn(api, 'listTasks').mockResolvedValue({
      tasks: [
        task({ SPACE: 2, AIR: 2 }, today), // 4 toward Vata
        task({ FIRE: 2, WATER: 2 }, today), // 4 toward Pitta, 2 of that Water also toward Kapha
        task({ EARTH: 4 }, today), // 4 toward Kapha
      ],
    })
    mockPlainTurn(true)
    render(<Codex />)
    await screen.findByText('The Codex of Elements')

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))

    // Fragments are summed across every task first, then split by dosha —
    // vata=4, pitta=4, kapha=6 (4 Earth + the 2 Water that Pitta also
    // claimed), out of 14 total. This is the water-double-counts-on-purpose
    // behaviour pinned in domain.test.ts, seen end to end through the chart.
    // find* (not get*) because the chart depends on the mocked listTasks
    // promise, which may still be settling relative to the navigation above.
    expect(
      await screen.findByRole('img', {
        name: 'Overall constitution: Vata 29%, Pitta 28%, Kapha 43%',
      }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('img', {
        name: "Today's constitution: Vata 29%, Pitta 28%, Kapha 43%",
      }),
    ).toBeInTheDocument()
  })

  it('shows both empty states in fiction when nothing has ever been logged', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    mockPlainTurn(true)
    render(<Codex />)
    await screen.findByText('The Codex of Elements')

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))

    expect(await screen.findByText('No deeds recorded yet.')).toBeInTheDocument()
    expect(screen.getByText("Today's page is still blank.")).toBeInTheDocument()
  })

  it('keeps Overall lit while Today goes blank, given only old history', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({
      tasks: [task({ SPACE: 5 }, '2020-01-01T00:00:00Z')],
    })
    mockPlainTurn(true)
    render(<Codex />)
    await screen.findByText('The Codex of Elements')

    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Next →' }))

    expect(
      screen.getByRole('img', { name: 'Overall constitution: Vata 100%, Pitta 0%, Kapha 0%' }),
    ).toBeInTheDocument()
    expect(screen.getByText("Today's page is still blank.")).toBeInTheDocument()
  })

  it('keeps the turning leaf and its faces out of the accessibility tree', async () => {
    vi.useFakeTimers()
    try {
      vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
      const { container } = render(<Codex />)
      // The initial fetch resolves over a microtask, which fake timers do
      // not touch, so this settles without advancing any timer — but the
      // resulting setState happens outside any RTL-instrumented call, so it
      // still needs its own act() to flush before the assertions below.
      await act(async () => {
        await Promise.resolve()
        await Promise.resolve()
      })

      expect(container.querySelector('.leaf')).not.toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: 'Next →' }))

      const leaf = container.querySelector('.leaf')
      expect(leaf).toBeInTheDocument()
      expect(leaf).toHaveAttribute('aria-hidden', 'true')
      expect(container.querySelectorAll('.leaf-face')).toHaveLength(2)
      // Still on the old spread until the leaf lands.
      expect(screen.getByText('The Codex of Elements')).toBeInTheDocument()

      // The turn commits from inside a setTimeout callback, outside any
      // RTL-instrumented event — act() is what makes React flush that state
      // update before the assertions below run.
      act(() => {
        vi.advanceTimersByTime(800)
      })
      expect(container.querySelector('.leaf')).not.toBeInTheDocument()
      expect(screen.getByText('The Five Elements')).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })
})
