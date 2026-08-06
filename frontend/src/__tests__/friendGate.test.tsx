import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { FriendGate } from '../components/FriendGate'
import { useSessionStore } from '../state/session'

beforeEach(() => {
  vi.restoreAllMocks()
  useSessionStore.setState({ authenticated: false, isTrial: false, error: null })
})

describe('FriendGate — gift link', () => {
  it('offers the gift form for a valid, ungifted link, and confirms after sending', async () => {
    vi.spyOn(api, 'checkFriend').mockResolvedValue({
      valid: true,
      name: 'alex',
      has_gifted: false,
    })
    const submit = vi.spyOn(api, 'submitFriendGift').mockResolvedValue({ ok: true })

    render(<FriendGate friendName="alex" />)

    const textarea = await screen.findByLabelText(/a gift for doslan/i)
    await userEvent.type(textarea, 'a weekend trip somewhere new')
    await userEvent.click(screen.getByRole('button', { name: /send it/i }))

    await waitFor(() => expect(submit).toHaveBeenCalledWith('alex', 'a weekend trip somewhere new'))
    expect(await screen.findByText(/sent — thank you/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/a gift for doslan/i)).not.toBeInTheDocument()
  })

  it('shows the confirmation immediately for an already-gifted link', async () => {
    vi.spyOn(api, 'checkFriend').mockResolvedValue({
      valid: true,
      name: 'alex',
      has_gifted: true,
    })

    render(<FriendGate friendName="alex" />)

    expect(await screen.findByText(/sent — thank you/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/a gift for doslan/i)).not.toBeInTheDocument()
  })

  it('still offers the trial alongside the gift form', async () => {
    vi.spyOn(api, 'checkFriend').mockResolvedValue({
      valid: true,
      name: 'alex',
      has_gifted: false,
    })

    render(<FriendGate friendName="alex" />)

    expect(await screen.findByRole('button', { name: /try it/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/a gift for doslan/i)).toBeInTheDocument()
  })

  it('shows no gift form for an unrecognised link', async () => {
    vi.spyOn(api, 'checkFriend').mockResolvedValue({
      valid: false,
      name: 'nobody',
      has_gifted: false,
    })

    render(<FriendGate friendName="nobody" />)

    expect(await screen.findByText(/isn.t one we recognise/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/a gift for doslan/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /try it/i })).not.toBeInTheDocument()
  })
})
