import { create } from 'zustand'

import { api, ApiError, setTrialToken } from '../api'

export interface SessionStore {
  authenticated: boolean
  isTrial: boolean
  checking: boolean
  error: string | null

  check: () => Promise<void>
  login: (password: string) => Promise<boolean>
  logout: () => Promise<void>
  startTrial: (friendName: string) => Promise<boolean>
}

export const useSessionStore = create<SessionStore>((set) => ({
  authenticated: false,
  isTrial: false,
  checking: true,
  error: null,

  check: async () => {
    set({ checking: true })
    try {
      const info = await api.session()
      set({ authenticated: info.authenticated, isTrial: info.is_trial, checking: false })
    } catch {
      set({ authenticated: false, isTrial: false, checking: false })
    }
  },

  login: async (password) => {
    set({ error: null })
    try {
      await api.login(password)
      set({ authenticated: true, isTrial: false })
      return true
    } catch (error) {
      set({
        error: error instanceof ApiError ? error.message : 'Could not sign in.',
        authenticated: false,
      })
      return false
    }
  },

  logout: async () => {
    try {
      await api.logout()
    } finally {
      setTrialToken(null)
      set({ authenticated: false, isTrial: false })
    }
  },

  startTrial: async (friendName) => {
    set({ error: null })
    try {
      const session = await api.startTrial(friendName)
      setTrialToken(session.token)
      set({ authenticated: true, isTrial: true })
      return true
    } catch (error) {
      set({
        error: error instanceof ApiError ? error.message : 'Could not start the trial.',
      })
      return false
    }
  },
}))
