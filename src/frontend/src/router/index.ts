import { createRouter, createWebHistory } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import AppShell from '@/layouts/AppShell.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import LoginView from '@/views/LoginView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import StyleGuideView from '@/views/StyleGuideView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', redirect: '/styleguide' },
        { path: 'styleguide', component: StyleGuideView, meta: { public: true } },
      ],
    },
    { path: '/403', component: ForbiddenView, meta: { public: true } },
    { path: '/:pathMatch(.*)*', component: NotFoundView, meta: { public: true } },
  ],
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
