import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import AppShell from '@/layouts/AppShell.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import LoginView from '@/views/LoginView.vue'
import NotFoundView from '@/views/NotFoundView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    section?: string
    public?: boolean
    roles?: string[]
  }
}

const isDev = import.meta.env.DEV

const children: RouteRecordRaw[] = [
  { path: '', redirect: '/dashboard' },
  {
    path: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '概览', section: '工作台' },
  },
  {
    path: 'tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { title: '任务', section: '教案', roles: ['teacher', 'lead'] },
  },
  {
    path: 'plans',
    component: () => import('@/views/PlansView.vue'),
    meta: { title: '教案库', section: '教案' },
  },
  {
    path: 'plans/:id',
    component: () => import('@/views/PlanDetailView.vue'),
    meta: { title: '教案详情', section: '教案' },
  },
]

if (isDev) {
  children.push({
    path: 'styleguide',
    component: () => import('@/views/StyleGuideView.vue'),
    meta: { public: true, title: '设计验收', section: '设计' },
  })
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: LoginView,
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: AppShell,
    children,
  },
  {
    path: '/403',
    component: ForbiddenView,
    meta: { public: true, title: '无权访问' },
  },
  {
    path: '/:pathMatch(.*)*',
    component: NotFoundView,
    meta: { public: true, title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    const reduceMotion =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (to.hash) return { el: to.hash, top: 24, behavior: reduceMotion ? 'auto' : 'smooth' }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const session = useSessionStore()
  if (!session.user) {
    const ok = await session.load()
    if (!ok) return { path: '/login', query: { redirect: to.fullPath } }
  }
  const roles = to.meta.roles
  if (roles && session.role && !roles.includes(session.role)) return '/403'
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 校本教案平台` : '校本教案平台'
})

export default router
