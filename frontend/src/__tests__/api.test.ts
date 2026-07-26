import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, getTrialToken, setTrialToken } from '../api'

function mockFetch(status: number, body: unknown) {
  const spy = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

beforeEach(() => {
  setTrialToken(null)
})

afterEach(() => {
  vi.unstubAllGlobals()
  setTrialToken(null)
})

describe('request plumbing', () => {
  it('returns the parsed body on success', async () => {
    mockFetch(200, { coins: 42 })
    await expect(api.collectables()).resolves.toEqual({ coins: 42 })
  })

  it('sends the session cookie', async () => {
    const spy = mockFetch(200, {})
    await api.state()
    expect(spy.mock.calls[0]?.[1]).toMatchObject({ credentials: 'include' })
  })

  it('omits the trial header when no token is set', async () => {
    const spy = mockFetch(200, {})
    await api.state()
    const headers = spy.mock.calls[0]?.[1]?.headers as Record<string, string>
    expect(headers['X-Trial-Token']).toBeUndefined()
  })

  it('sends the trial header once a token is set', async () => {
    setTrialToken('tok-123')
    const spy = mockFetch(200, {})
    await api.state()
    const headers = spy.mock.calls[0]?.[1]?.headers as Record<string, string>
    expect(headers['X-Trial-Token']).toBe('tok-123')
  })

  it('serialises the body and sets the content type', async () => {
    const spy = mockFetch(200, {})
    await api.completeTask('went for a run')
    const init = spy.mock.calls[0]?.[1] as RequestInit
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ text: 'went for a run' }))
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
  })

  it('tolerates an empty response body', async () => {
    mockFetch(200, undefined)
    await expect(api.logout()).resolves.toBeNull()
  })
})

describe('error envelope', () => {
  it('maps the server error envelope onto ApiError', async () => {
    mockFetch(400, { error: { code: 'INSUFFICIENT_COINS', message: 'Not enough coins.' } })

    await expect(api.buyTreasure('t1')).rejects.toMatchObject({
      code: 'INSUFFICIENT_COINS',
      message: 'Not enough coins.',
      status: 400,
    })
  })

  it('carries key_needed through on MISSING_KEY', async () => {
    mockFetch(400, {
      error: {
        code: 'MISSING_KEY',
        message: 'missing key: one OCEAN ESSENCE required',
        key_needed: { element: 'OCEAN', rarity: 'ESSENCE' },
      },
    })

    const error = await api.openReceptacle('r1').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).keyNeeded).toEqual({ element: 'OCEAN', rarity: 'ESSENCE' })
  })

  it('maps a 401 to UNAUTHENTICATED', async () => {
    mockFetch(401, { error: { code: 'UNAUTHENTICATED', message: 'Sign in.' } })
    await expect(api.state()).rejects.toMatchObject({ code: 'UNAUTHENTICATED', status: 401 })
  })

  it('flattens DRF field validation errors into a readable message', async () => {
    mockFetch(400, { text: ['This field may not be blank.'] })

    const error = (await api.completeTask('').catch((e: unknown) => e)) as ApiError
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(error.message).toContain('This field may not be blank.')
  })

  it('falls back gracefully when the body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500, text: async () => '<html>oops' }),
    )

    const error = (await api.state().catch((e: unknown) => e)) as ApiError
    expect(error.code).toBe('ERROR')
    expect(error.status).toBe(500)
  })
})

describe('trial token storage', () => {
  it('persists and clears the token', () => {
    setTrialToken('abc')
    expect(getTrialToken()).toBe('abc')
    setTrialToken(null)
    expect(getTrialToken()).toBeNull()
  })
})
