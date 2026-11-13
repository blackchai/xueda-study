import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearAuthenticatedUser, getAuthenticatedUser, setAuthenticatedUser } from './authSession'

afterEach(() => { clearAuthenticatedUser(); vi.unstubAllGlobals() })
describe('认证内存缓存的异步边界', () => {
  it('退出后迟到的 me 响应不能恢复旧用户或覆盖新用户', async () => {
    clearAuthenticatedUser()
    let resolve!: (value: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(r => { resolve = r })))
    const pending = getAuthenticatedUser()
    clearAuthenticatedUser()
    const next = { userId: 'b', displayName: 'B', onboardingCompleted: false }
    setAuthenticatedUser(next)
    resolve(new Response(JSON.stringify({ code: 0, data: { userId: 'a', displayName: 'A' } })))
    await expect(pending).rejects.toThrow('登录状态已改变')
    expect(await getAuthenticatedUser()).toEqual(next)
  })
})
