import { defineStore } from 'pinia'

export type ThemeName = 'ink' | 'pine'

export const useUiStore = defineStore('ui', {
  state: () => ({
    theme: (localStorage.getItem('lpp-theme') as ThemeName) || 'ink',
    sidebarCollapsed: false,
  }),
  actions: {
    setTheme(theme: ThemeName): void {
      this.theme = theme
      document.documentElement.dataset.theme = theme
      localStorage.setItem('lpp-theme', theme)
    },
    toggleSidebar(): void {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
  },
})
