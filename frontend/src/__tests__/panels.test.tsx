import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { MergePanel } from '../components/MergePanel'
import { RewardComposer } from '../components/RewardComposer'
import { TaskComposer } from '../components/TaskComposer'
import { useGameStore } from '../state/store'
import { stockKey, type Stocks } from '../types'

function setStocks(stocks: Stocks) {
  useGameStore.setState({ stocks })
}

beforeEach(() => {
  useGameStore.getState().reset()
})

describe('TaskComposer', () => {
  it('cannot submit an empty task', () => {
    render(<TaskComposer />)
    expect(screen.getByRole('button', { name: /log it/i })).toBeDisabled()
  })
})

describe('RewardComposer', () => {
  it('does not mask the textarea for your own rewards', () => {
    render(<RewardComposer friends={[]} />)
    const textarea = screen.getByLabelText(/reward description/i)
    expect(textarea).not.toHaveClass('masked')
  })

  it('masks the textarea for a secret gift', async () => {
    const user = userEvent.setup()
    render(<RewardComposer friends={[{ name: 'alex', url: 'https://x/alex' }]} />)

    await user.click(screen.getByRole('tab', { name: /secret gift/i }))

    const textarea = screen.getByLabelText(/secret gift text \(hidden\)/i)
    expect(textarea).toHaveClass('masked')
  })

  it('requires a friend before a secret gift can be sealed', async () => {
    const user = userEvent.setup()
    render(<RewardComposer friends={[{ name: 'alex', url: 'https://x/alex' }]} />)
    await user.click(screen.getByRole('tab', { name: /secret gift/i }))

    await user.type(screen.getByLabelText(/secret gift text/i), 'a promise')
    expect(screen.getByRole('button', { name: /seal it away/i })).toBeDisabled()

    await user.selectOptions(screen.getByLabelText(/friend/i), 'alex')
    expect(screen.getByRole('button', { name: /seal it away/i })).toBeEnabled()
  })

  it('clears the text when switching modes so a pasted secret cannot leak', async () => {
    const user = userEvent.setup()
    render(<RewardComposer friends={[{ name: 'alex', url: 'https://x/alex' }]} />)

    await user.click(screen.getByRole('tab', { name: /secret gift/i }))
    await user.type(screen.getByLabelText(/secret gift text/i), 'top secret')
    await user.click(screen.getByRole('tab', { name: /for me/i }))

    expect(screen.getByLabelText(/reward description/i)).toHaveValue('')
  })
})

describe('MergePanel', () => {
  it('shows nothing to do with an empty inventory', () => {
    render(<MergePanel />)
    expect(screen.getByText(/log a task to earn your first fragments/i)).toBeInTheDocument()
  })

  it('disables the harmony merge until all five base elements are held', () => {
    setStocks({
      [stockKey('SPACE', 'FRAGMENT')]: 1,
      [stockKey('AIR', 'FRAGMENT')]: 1,
      [stockKey('FIRE', 'FRAGMENT')]: 1,
      [stockKey('WATER', 'FRAGMENT')]: 1,
    })
    render(<MergePanel />)

    expect(screen.getByRole('button', { name: /merge to harmony/i })).toBeDisabled()
  })

  it('enables the harmony merge once all five are held', () => {
    setStocks({
      [stockKey('SPACE', 'FRAGMENT')]: 1,
      [stockKey('AIR', 'FRAGMENT')]: 1,
      [stockKey('FIRE', 'FRAGMENT')]: 1,
      [stockKey('WATER', 'FRAGMENT')]: 1,
      [stockKey('EARTH', 'FRAGMENT')]: 1,
    })
    render(<MergePanel />)

    expect(screen.getByRole('button', { name: /merge to harmony/i })).toBeEnabled()
  })

  it('disables combine when the harmony is missing', () => {
    setStocks({
      [stockKey('EARTH', 'FRAGMENT')]: 1,
      [stockKey('WATER', 'FRAGMENT')]: 1,
    })
    render(<MergePanel />)

    expect(screen.getByRole('button', { name: /^combine$/i })).toBeDisabled()
  })

  it('enables combine once both bases and a harmony are held', () => {
    setStocks({
      [stockKey('EARTH', 'FRAGMENT')]: 1,
      [stockKey('WATER', 'FRAGMENT')]: 1,
      [stockKey('HARMONY', 'FRAGMENT')]: 1,
    })
    render(<MergePanel />)

    expect(screen.getByRole('button', { name: /^combine$/i })).toBeEnabled()
  })

  it('only lists elements the player actually holds', () => {
    setStocks({ [stockKey('FIRE', 'FRAGMENT')]: 2 })
    render(<MergePanel />)

    expect(screen.getByRole('rowheader', { name: /fire/i })).toBeInTheDocument()
    expect(screen.queryByRole('rowheader', { name: /ocean/i })).not.toBeInTheDocument()
  })
})
