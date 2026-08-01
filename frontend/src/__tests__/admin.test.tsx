import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { Admin } from '../layouts/Admin'
import { RewardList } from '../layouts/RewardList'
import { useGameStore } from '../state/store'
import type { FriendLink, Reward } from '../types'

// Every rarity/virtue string that could conceivably leak. If a Reward object
// ever grows one of these fields, this list is what a leak test would need
// to check for -- kept here so the intent is explicit rather than guessed at
// from the enum module.
const RARITY_WORDS = [
  'POUCH', 'SACK', 'CHEST', 'SAFE', 'VAULT', 'SANCTUM',
  'FRAGMENT', 'SHARD', 'CRYSTAL', 'ESSENCE', 'SOUL', 'CORE',
]
const VIRTUE_WORDS = [
  'NURTURING', 'DETERMINATION', 'ADAPTABILITY', 'PRESENCE', 'TRANSFORMATION',
  'REFLECTION', 'SERENITY', 'INSPIRATION', 'VITALITY', 'FREEDOM',
]

function reward(overrides: Partial<Reward> = {}): Reward {
  return {
    text: 'a weekend in the mountains',
    is_secret: false,
    friend_name: null,
    created_at: new Date().toISOString(),
    is_opened: false,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useGameStore.setState({ events: [] })
})

describe('RewardList', () => {
  it('never renders a virtue or rarity string, however the fixture is shaped', () => {
    // Reward carries none of these fields at the type level -- this is the
    // belt-and-braces check that nothing sneaks one into the rendered text.
    const rewards = [
      reward({ text: 'A weekend in the mountains' }),
      reward({ text: 'New running shoes', is_opened: true }),
      reward({ is_secret: true, friend_name: 'alex', text: null }),
      reward({ is_secret: true, friend_name: 'sam', text: 'opened now', is_opened: true }),
    ]
    render(<RewardList rewards={rewards} loading={false} />)

    const dom = document.body.textContent ?? ''
    for (const word of [...RARITY_WORDS, ...VIRTUE_WORDS]) {
      expect(dom).not.toContain(word)
    }
  })

  it('shows the owner their own text', () => {
    render(<RewardList rewards={[reward({ text: 'New headphones' })]} loading={false} />)
    expect(screen.getByText('New headphones')).toBeInTheDocument()
    expect(screen.getByText('yours')).toBeInTheDocument()
  })

  it("masks a friend's secret gift until it has been opened", () => {
    render(
      <RewardList
        rewards={[reward({ is_secret: true, friend_name: 'alex', text: null })]}
        loading={false}
      />,
    )

    expect(screen.getByText(/hidden until it opens/i)).toBeInTheDocument()
    expect(screen.getByText(/secret · alex/i)).toBeInTheDocument()
    expect(screen.queryByText('opened')).not.toBeInTheDocument()
  })

  it('reveals a secret gift once the server says it was opened', () => {
    render(
      <RewardList
        rewards={[
          reward({
            is_secret: true,
            friend_name: 'alex',
            text: 'the thing alex actually sent',
            is_opened: true,
          }),
        ]}
        loading={false}
      />,
    )

    expect(screen.getByText('the thing alex actually sent')).toBeInTheDocument()
    expect(screen.getByText('opened')).toBeInTheDocument()
  })

  it('says so when nothing has been sealed yet', () => {
    render(<RewardList rewards={[]} loading={false} />)
    expect(screen.getByText(/nothing sealed away yet/i)).toBeInTheDocument()
  })
})

describe('Admin page', () => {
  it('lists rewards fetched from GET /api/rewards', async () => {
    vi.spyOn(api, 'listFriends').mockResolvedValue({ friends: [] })
    vi.spyOn(api, 'listRewards').mockResolvedValue({
      rewards: [reward({ text: 'Dinner at the impossible place' })],
    })

    render(<Admin />)

    expect(await screen.findByText('Dinner at the impossible place')).toBeInTheDocument()
  })

  it('sealing a reward refreshes the list', async () => {
    vi.spyOn(api, 'listFriends').mockResolvedValue({ friends: [] })
    const listRewards = vi
      .spyOn(api, 'listRewards')
      .mockResolvedValueOnce({ rewards: [] })
      .mockResolvedValueOnce({ rewards: [reward({ text: 'New headphones' })] })
    useGameStore.setState({ submitReward: async () => true })

    render(<Admin />)
    await waitFor(() => expect(screen.getByText(/nothing sealed away yet/i)).toBeInTheDocument())

    await userEvent.type(
      screen.getByLabelText(/a reward worth working toward/i),
      'New headphones',
    )
    await userEvent.click(screen.getByRole('button', { name: /seal it/i }))

    expect(await screen.findByText('New headphones')).toBeInTheDocument()
    expect(listRewards).toHaveBeenCalledTimes(2)
  })

  it('shows a created friend link for sharing', async () => {
    vi.spyOn(api, 'listFriends').mockResolvedValue({ friends: [] })
    vi.spyOn(api, 'listRewards').mockResolvedValue({ rewards: [] })
    const link: FriendLink = { name: 'alex', url: 'https://lifu.doslan.com/alex' }
    vi.spyOn(api, 'createFriend').mockResolvedValue(link)

    render(<Admin />)
    await waitFor(() => expect(screen.getByLabelText(/friend name/i)).toBeInTheDocument())

    await userEvent.type(screen.getByLabelText(/friend name/i), 'alex')
    await userEvent.click(screen.getByRole('button', { name: /create link/i }))

    expect(await screen.findByText('https://lifu.doslan.com/alex')).toBeInTheDocument()
  })

  it('offers the secret-gift friend selector only once a friend exists', async () => {
    vi.spyOn(api, 'listFriends').mockResolvedValue({
      friends: [{ name: 'sam', url: 'https://lifu.doslan.com/sam' }],
    })
    vi.spyOn(api, 'listRewards').mockResolvedValue({ rewards: [] })

    render(<Admin />)
    await userEvent.click(await screen.findByRole('tab', { name: /secret gift/i }))

    const select = within(screen.getByLabelText('Friend'))
    expect(select.getByText('sam')).toBeInTheDocument()
  })

  it('states the privacy rule in the page itself', async () => {
    vi.spyOn(api, 'listFriends').mockResolvedValue({ friends: [] })
    vi.spyOn(api, 'listRewards').mockResolvedValue({ rewards: [] })

    render(<Admin />)

    expect(
      await screen.findByText(/you cannot see which receptacle holds what/i),
    ).toBeInTheDocument()
  })
})
