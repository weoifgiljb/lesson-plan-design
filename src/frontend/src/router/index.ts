import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import AppShell from '@/layouts/AppShell.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import LoginView from '@/views/LoginView.vue'
import NotFoundView from '@/views/NotFoundView.vue'

const isDev = import.meta.env.DEV

const children: RouteRecordRaw[] = [{ path: '', redirect: isDev ? '/styleguide' : '/login' }]
if (isDev) {
  children.push({
    path: 'styleguide',
    component: () => import('@/views/StyleGuideView.vue'),
    meta: { public: true },
  })
}

const routes: RouteRecordRaw[] = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/', component: AppShell, children },
  { path: '/403', component: ForbiddenView, meta: { public: true } },
  { path: '/:pathMatch(.*)*', component: NotFoundView, meta: { public: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const session = useSessionStore()
  if (!session.user) {
    const ok = await session.load()
    if (!ok) return { path: '/login', query: { redirect: to.fullPath } }
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && session.role && !roles.includes(session.role)) return '/403'
  return true
})

export default router
