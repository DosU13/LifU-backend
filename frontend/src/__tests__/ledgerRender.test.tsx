import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { Ledger } from '../layouts/Ledger'
import { useGameStore } from '../state/store'
import type { Task, TaskCompletion } from '../types'

function task(id: string, overrides: Partial<Task> = {}): Task {
  return {
    id,
    text: `did thing ${id}`,
    created_at: new Date().toISOString(),
    value: 20,
    virtues: { AWARENESS: 0, CURIOSITY: 0, WILLPOWER: 50, COMPASSION: 0, DISCIPLINE: 0 },
    fragments_awarded: { FIRE: 13 },
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useGameStore.setState({ events: [] })
})

describe('Ledger', () => {
  it('says something friendly when nothing has been logged', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })

    render(<Ledger />)

    expect(await screen.findByText(/nothing logged yet/i)).toBeInTheDocument()
  })

  it('shows four tasks, then expands on "more"', async () => {
    const tasks = Array.from({ length: 9 }, (_, i) => task(`t${i}`))
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks })

    render(<Ledger />)

    await waitFor(() => expect(screen.getByText('did thing t0')).toBeInTheDocument())
    expect(screen.queryByText('did thing t4')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /more/i }))

    expect(screen.getByText('did thing t8')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /more/i })).not.toBeInTheDocument()
  })

  it('hides "more" when everything already fits', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [task('a'), task('b')] })

    render(<Ledger />)

    await waitFor(() => expect(screen.getByText('did thing a')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /more/i })).not.toBeInTheDocument()
  })

  it('replays exactly the drops the server returned, in order', async () => {
    // Three fragments back means three reveal cards -- no more, no fewer, and
    // never a count the client made up.
    const completion: TaskCompletion = {
      task: { value: 42, virtues: {} as Task['virtues'] },
      fragments_awarded: { FIRE: 13, EARTH: 8, SPACE: 5 },
    }
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    vi.spyOn(useGameStore.getState(), 'completeTask')
    useGameStore.setState({ completeTask: async () => completion })

    render(<Ledger />)

    await userEvent.type(screen.getByLabelText(/what did you get done/i), 'ran 10km')
    await userEvent.click(screen.getByRole('button', { name: /claim/i }))

    expect(await screen.findByText('Fire Fragment')).toBeInTheDocument()
    expect(screen.getByText('×13')).toBeInTheDocument()
    // The virtue that paid for it, from the mapping mirror.
    expect(screen.getByText('willpower')).toBeInTheDocument()

    // Skip is offered because more than one prize is queued.
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText('Earth Fragment')).toBeInTheDocument()
    expect(screen.getByText('discipline')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText('Space Fragment')).toBeInTheDocument()

    // Last card closes rather than advancing into nothing.
    await userEvent.click(screen.getByRole('button', { name: /done/i }))
    await waitFor(() => expect(screen.queryByText('Space Fragment')).not.toBeInTheDocument())
  })

  it('offers no skip when a single fragment came back', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    useGameStore.setState({
      completeTask: async () => ({
        task: { value: 9, virtues: {} as Task['virtues'] },
        fragments_awarded: { WATER: 4 },
      }),
    })

    render(<Ledger />)

    await userEvent.type(screen.getByLabelText(/what did you get done/i), 'called mum')
    await userEvent.click(screen.getByRole('button', { name: /claim/i }))

    expect(await screen.findByText('Water Fragment')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /skip all/i })).not.toBeInTheDocument()
  })

  it('does not open a reveal when the task paid nothing', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })
    useGameStore.setState({
      completeTask: async () => ({
        task: { value: 1, virtues: {} as Task['virtues'] },
        fragments_awarded: {},
      }),
    })

    render(<Ledger />)

    await userEvent.type(screen.getByLabelText(/what did you get done/i), 'blinked')
    await userEvent.click(screen.getByRole('button', { name: /claim/i }))

    await waitFor(() =>
      expect(screen.getByLabelText(/what did you get done/i)).toHaveValue(''),
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('will not submit an empty or whitespace-only task', async () => {
    vi.spyOn(api, 'listTasks').mockResolvedValue({ tasks: [] })

    render(<Ledger />)

    const claim = screen.getByRole('button', { name: /claim/i })
    expect(claim).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/what did you get done/i), '   ')
    expect(claim).toBeDisabled()
  })
})
