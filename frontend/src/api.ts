import type {
  BuyResult,
  CollectableRarity,
  Element,
  FriendLink,
  GameState,
  HarmonyResult,
  OpenResult,
  Receptacle,
  ReceptacleState,
  Reward,
  SessionInfo,
  Stats,
  Stocks,
  Task,
  TaskCompletion,
  Treasure,
} from './types'

/**
 * A failure the server described in its `{"error": {code, message}}` envelope.
 * `code` is the stable identifier to branch on; `message` is for humans.
 */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  /** Present on MISSING_KEY: which collectable the receptacle needs. */
  readonly keyNeeded: { element: Element; rarity: CollectableRarity } | undefined

  constructor(
    code: string,
    message: string,
    status: number,
    keyNeeded?: { element: Element; rarity: CollectableRarity },
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.keyNeeded = keyNeeded
  }
}

/**
 * Held in memory only, never persisted. A trial is meant to be a place to
 * poke at the mechanics — reloading the page starts a fresh one rather than
 * resuming, which is exactly what a sandbox should do.
 */
let trialToken: string | null = null

export function setTrialToken(token: string | null): void {
  trialToken = token
}

export function getTrialToken(): string | null {
  return trialToken
}

function extractError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object' && 'error' in body) {
    const envelope = (body as { error: unknown }).error
    if (envelope && typeof envelope === 'object') {
      const { code, message, key_needed: keyNeeded } = envelope as {
        code?: unknown
        message?: unknown
        key_needed?: { element: Element; rarity: CollectableRarity }
      }
      return new ApiError(
        typeof code === 'string' ? code : 'ERROR',
        typeof message === 'string' ? message : 'Request failed.',
        status,
        keyNeeded,
      )
    }
  }
  // DRF field-validation errors (400) arrive as {field: [messages]}.
  if (body && typeof body === 'object') {
    const parts: string[] = []
    for (const [field, messages] of Object.entries(body as Record<string, unknown>)) {
      const text = Array.isArray(messages) ? messages.join(' ') : String(messages)
      parts.push(`${field}: ${text}`)
    }
    if (parts.length > 0) {
      return new ApiError('VALIDATION_ERROR', parts.join('; '), status)
    }
  }
  return new ApiError('ERROR', `Request failed (${status}).`, status)
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getTrialToken()
  if (token) headers['X-Trial-Token'] = token

  const init: RequestInit = {
    method: options.method ?? 'GET',
    headers,
    // Carries the owner's session cookie.
    credentials: 'include',
  }
  if (options.body !== undefined) init.body = JSON.stringify(options.body)

  const response = await fetch(`/api${path}`, init)

  let payload: unknown = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) throw extractError(response.status, payload)
  return payload as T
}

export const api = {
  // --- session ---
  session: () => request<SessionInfo>('/auth/session'),
  login: (password: string) =>
    request<{ ok: boolean }>('/auth/login', { method: 'POST', body: { password } }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),

  // --- world ---
  state: () => request<GameState>('/state'),
  stats: () => request<Stats>('/stats'),

  // --- tasks ---
  completeTask: (text: string) =>
    request<TaskCompletion>('/tasks', { method: 'POST', body: { text } }),
  listTasks: (days = 30) => request<{ tasks: Task[] }>(`/tasks?days=${days}`),

  // --- collectables ---
  collectables: () => request<{ stocks: Stocks; coins: number }>('/collectables'),
  merge: (element: Element, rarity: CollectableRarity) =>
    request<{ stocks: Stocks }>('/collectables/merge', {
      method: 'POST',
      body: { element, rarity },
    }),
  harmony: (rarity: CollectableRarity) =>
    request<HarmonyResult>('/collectables/harmony', { method: 'POST', body: { rarity } }),
  combine: (elementA: Element, elementB: Element, rarity: CollectableRarity) =>
    request<{ result_element: Element; stocks: Stocks }>('/collectables/combine', {
      method: 'POST',
      body: { element_a: elementA, element_b: elementB, rarity },
    }),
  sell: (element: Element, rarity: CollectableRarity, count: number) =>
    request<{ coins: number; stocks: Stocks }>('/collectables/sell', {
      method: 'POST',
      body: { element, rarity, count },
    }),

  // --- rewards and receptacles ---
  // Answers with the reward, never the receptacle it was sealed into.
  submitReward: (text: string, isSecret = false, friendName?: string) =>
    request<Reward>('/rewards', {
      method: 'POST',
      body: { text, is_secret: isSecret, ...(friendName ? { friend_name: friendName } : {}) },
    }),
  listRewards: () => request<{ rewards: Reward[] }>('/rewards'),
  listReceptacles: (state: ReceptacleState = 'DROPPED') =>
    request<{ receptacles: Receptacle[] }>(`/receptacles?state=${state}`),
  openReceptacle: (id: string) =>
    request<OpenResult>(`/receptacles/${id}/open`, { method: 'POST' }),

  // --- treasures ---
  treasures: () => request<{ treasures: Treasure[] }>('/treasures'),
  buyTreasure: (id: string) => request<BuyResult>(`/treasures/${id}/buy`, { method: 'POST' }),
  discardTreasure: (id: string) =>
    request<{ new_treasure: Treasure | null }>(`/treasures/${id}/discard`, { method: 'POST' }),

  // --- friends and trial ---
  listFriends: () => request<{ friends: FriendLink[] }>('/friends'),
  createFriend: (name: string) =>
    request<FriendLink>('/friends', { method: 'POST', body: { name } }),
  checkFriend: (name: string) =>
    request<{ valid: boolean; name: string }>(`/public/friend/${name}`),
  startTrial: (friendName: string) =>
    request<{ token: string; friend_name: string; expires_at: string }>('/trial/session', {
      method: 'POST',
      body: { friend_name: friendName },
    }),
}
