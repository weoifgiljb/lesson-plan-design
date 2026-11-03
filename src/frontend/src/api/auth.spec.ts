import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn()
const get = vi.fn()

vi.mock('./client', () => ({
  client: {
    post: (...args: unknown[]) => post(...args),
    get: (...args: unknown[]) => get(...args),
  },
}))

const { register, changePassword, fetchMe, fetchAuthMe, exchangeToken } = await import('./auth')

describe('api/auth.ts', () => {
  beforeEach(() => {
    post.mockReset()
    get.mockReset()
  })

  it('注册调用 /api/v1/auth/register 并透传表单', async () => {
    post.mockResolvedValue({ user: { id: 7 }, accessToken: 't' })
    const payload = { username: 'teacher9', displayName: '张老师', password: 'Lesson2026' }
    await register(payload)
    expect(post).toHaveBeenCalledWith('/api/v1/auth/register', payload)
  })

  it('改密调用 /api/v1/me/password', async () => {
    post.mockResolvedValue({ ok: true })
    await changePassword({ oldPassword: 'Lesson2026', newPassword: 'Lesson2027' })
    expect(post).toHaveBeenCalledWith('/api/v1/me/password', {
      oldPassword: 'Lesson2026',
      newPassword: 'Lesson2027',
    })
  })

  it('会话身份仍走 /api/v1/me（Cookie 通道）', async () => {
    get.mockResolvedValue({ user: { id: 1 }, csrfToken: 'c' })
    await fetchMe()
    expect(get).toHaveBeenCalledWith('/api/v1/me')
  })

  it('换令牌与 Bearer 身份查询走 /auth/token、/auth/me', async () => {
    post.mockResolvedValue({ accessToken: 't' })
    get.mockResolvedValue({ user: { id: 1 }, auth: 'jwt' })
    await exchangeToken('teacher9', 'Lesson2026')
    await fetchAuthMe()
    expect(post).toHaveBeenCalledWith('/api/v1/auth/token', {
      username: 'teacher9',
      password: 'Lesson2026',
    })
    expect(get).toHaveBeenCalledWith('/api/v1/auth/me')
  })
})
