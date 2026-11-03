import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'

import ChangePasswordView from './ChangePasswordView.vue'
import { RequestError } from '@/api/client-error'

const changePassword = vi.fn()
const signOut = vi.fn().mockResolvedValue(undefined)

vi.mock('@/api/auth', () => ({
  changePassword: (...args: unknown[]) => changePassword(...args),
  login: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
}))

vi.mock('@/stores/session', () => ({
  useSessionStore: () => ({ signOut }),
}))

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/change-password', component: ChangePasswordView },
      { path: '/login', component: { template: '<div />' } },
      { path: '/dashboard', component: { template: '<div />' } },
    ],
  })
}

async function mountView() {
  const router = buildRouter()
  await router.push('/change-password')
  await router.isReady()
  const wrapper = mount(ChangePasswordView, {
    global: { plugins: [ElementPlus, createPinia(), router] },
  })
  return { wrapper, router }
}

async function fillForm(wrapper: Awaited<ReturnType<typeof mountView>>['wrapper']) {
  await wrapper.find('input[autocomplete="current-password"]').setValue('Lesson2026')
  const [newPassword, confirm] = wrapper.findAll('input[autocomplete="new-password"]')
  await newPassword.setValue('Lesson2027')
  await confirm.setValue('Lesson2027')
}

describe('ChangePasswordView', () => {
  it('改密成功后清会话并回登录页', async () => {
    changePassword.mockResolvedValue({ ok: true })
    const { wrapper, router } = await mountView()
    await fillForm(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(changePassword).toHaveBeenCalledWith({
      oldPassword: 'Lesson2026',
      newPassword: 'Lesson2027',
    })
    expect(signOut).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.changed).toBe('1')
  })

  it('旧口令错误时展示后端文案与 traceId', async () => {
    changePassword.mockRejectedValue(
      new RequestError({
        code: 'AUTH_REQUIRED',
        message: '原口令不正确',
        status: 401,
        traceId: 'trace-9',
        details: {},
      }),
    )
    const { wrapper, router } = await mountView()
    await fillForm(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('原口令不正确')
    expect(wrapper.find('[role="alert"]').text()).toContain('trace-9')
    expect(router.currentRoute.value.path).toBe('/change-password')
  })

  it('提供退出登录入口（不再引导去 dashboard）', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('退出登录')
    expect(wrapper.text()).not.toContain('稍后再说')
  })
})
