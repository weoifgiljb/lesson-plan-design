import { defineStore } from 'pinia'

import { fetchMe, login, logout } from '@/api/auth'
import type { User } from '@/api/models'

export const useSessionStore = defineStore('session', {
  state: () => ({
    user: null as User | null,
    loading: false,
  }),
  getters: {
    role: (state) => state.user?.role ?? '',
    isAdmin: (state) => state.user?.role === 'admin',
    isLead: (state) => state.user?.role === 'lead',
  },
  actions: {
    async load(): Promise<boolean> {
      this.loading = true
      try {
        const result = await fetchMe()
        this.user = result.user
        return true
      } catch {
        this.user = null
        return false
      } finally {
        this.loading = false
      }
    },
    async signIn(username: string, password: string): Promise<void> {
      const result = await login({ username, password })
      this.user = result.user
    },
    async signOut(): Promise<void> {
      try {
        await logout()
      } finally {
        this.user = null
      }
    },
  },
})
