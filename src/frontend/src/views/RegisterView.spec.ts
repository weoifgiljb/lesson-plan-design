import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import RegisterView from './RegisterView.vue'
import { RequestError } from '@/api/client-error'

const register = vi.fn()

vi.mock('@/api/auth', () => ({
  register: (...args: unknown[]) => register(...args),
}))

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/register', component: RegisterView },
      { path: '/login', component: { template: '<div />' } },
    ],
  })
}

async function mountView() {
  const router = buildRouter()
  await router.push('/register')
  await router.isReady()
  const wrapper = mount(RegisterView, {
    global: { plugins: [ElementPlus, router] },
  })
  return { wrapper, router }
}

async function fill(wrapper: Awaited<ReturnType<typeof mountView>>['wrapper'], values: Record<string, string>) {
  for (const [field, value] of Object.entries(values)) {
    await wrapper.find(`input[autocomplete="${field}"]`).setValue(value)
  }
}

describe('RegisterView', () => {
  it('提交成功后跳到登录页并带 registered 标记', async () => {
    register.mockResolvedValue({ user: { id: 9 }, accessToken: 't' })
    const { wrapper, router } = await mountView()
    await fill(wrapper, {
      username: 'teacher9',
      name: '张老师',
      'new-password': 'Lesson2026',
    })
    // 确认口令是第二个 new-password 输入
    const newPasswordInputs = wrapper.findAll('input[autocomplete="new-password"]')
    await newPasswordInputs[1].setValue('Lesson2026')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(register).toHaveBeenCalledWith({
      username: 'teacher9',
      displayName: '张老师',
      password: 'Lesson2026',
    })
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.registered).toBe('1')
  })

  it('用户名占用时展示错误文案与 traceId，不跳转', async () => {
    register.mockRejectedValue(
      new RequestError({
        code: 'USERNAME_TAKEN',
        message: '用户名已被占用，请换一个',
        status: 409,
        traceId: 'trace-1',
        details: {},
      }),
    )
    const { wrapper, router } = await mountView()
    await fill(wrapper, {
      username: 'taken',
      name: '张老师',
      'new-password': 'Lesson2026',
    })
    await wrapper.findAll('input[autocomplete="new-password"]')[1].setValue('Lesson2026')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const alert = wrapper.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('用户名已被占用')
    expect(alert.text()).toContain('trace-1')
    expect(router.currentRoute.value.path).toBe('/register')
  })
})
