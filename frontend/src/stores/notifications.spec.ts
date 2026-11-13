import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useNotificationStore } from './notifications'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())
const response = (count: number) => new Response(JSON.stringify({ code: 0, data: { unreadCount: count } }))

describe('全站未读数共享与账号隔离', () => {
  it('同时刷新复用同一请求，并对短时间重复查询节流', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(response(3)))
    vi.stubGlobal('fetch', fetcher)
    const store = useNotificationStore()
    await Promise.all([store.refreshCount(), store.refreshCount(), store.refreshCount()])
    await store.refreshCount()
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(store.unreadCount).toBe(3)
  })
  it('标记已读更新后，较早轮询响应不能恢复旧未读数', async () => {
    let resolve!: (value: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(r => { resolve = r })))
    const store = useNotificationStore()
    const pending = store.refreshCount()
    store.acceptCount(0)
    resolve(response(8))
    await pending
    expect(store.unreadCount).toBe(0)
  })
  it('退出并切换账号后，旧账号迟到响应被丢弃', async () => {
    let resolve!: (value: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(r => { resolve = r })))
    const store = useNotificationStore()
    const pending = store.refreshCount()
    store.reset(); store.acceptCount(2)
    resolve(response(99))
    await pending
    expect(store.unreadCount).toBe(2)
  })
  it('网络失败显示同步错误且保留已知数值，不伪造已读', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const store = useNotificationStore()
    store.acceptCount(4)
    await store.refreshCount(true)
    expect(store.error).toContain('无法连接')
    expect(store.unreadCount).toBe(4)
    expect(store.expired).toBe(false)
  })
  it('401使内存通知失效，由全站布局处理重新登录', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'UNAUTHENTICATED', message: '会话失效' }), { status: 401 })))
    const store = useNotificationStore()
    store.acceptCount(5)
    await store.refreshCount(true)
    expect(store.unreadCount).toBe(0)
    expect(store.expired).toBe(true)
  })
})
