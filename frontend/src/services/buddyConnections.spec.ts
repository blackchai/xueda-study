import { afterEach, describe, expect, it, vi } from 'vitest'

import { buddyConnectionsApi } from './buddyConnections'

afterEach(() => vi.unstubAllGlobals())
function response(data: unknown, status = 200): Response {
  return new Response(JSON.stringify({ code: status >= 400 ? 'BUDDY_REQUEST_CLOSED' : 0, message: status >= 400 ? '邀请已处理' : 'ok', data }), { status })
}

describe('真实邀请、关系与通知 API', () => {
  it('未读数量和全部已读使用当前会话，不提交用户身份', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ unreadCount: 3 })).mockResolvedValueOnce(response({ updatedCount: 3, unreadCount: 0 }))
    vi.stubGlobal('fetch', fetcher)
    expect((await buddyConnectionsApi.unreadCount()).unreadCount).toBe(3)
    expect((await buddyConnectionsApi.readAllNotifications()).updatedCount).toBe(3)
    expect(fetcher.mock.calls[0]![0]).toBe('/api/v1/notifications/unread-count')
    expect(fetcher.mock.calls[1]![1].method).toBe('PATCH')
    expect(fetcher.mock.calls[1]![1].body).toBeUndefined()
  })
  it('邀请只发送接收者和留言，身份由 Cookie 提供', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ id: 'request-1', status: 'pending' }, 201))
    vi.stubGlobal('fetch', fetchMock)
    const result = await buddyConnectionsApi.sendInvitation('recipient-uuid', '一起学习')
    const [url, options] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/buddy-requests')
    expect(options.credentials).toBe('include')
    expect(JSON.parse(options.body)).toEqual({ recipientId: 'recipient-uuid', message: '一起学习' })
    expect(result.status).toBe('pending')
  })
  it('后端状态冲突向界面抛错，不生成本地成功状态', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(null, 409)))
    await expect(buddyConnectionsApi.resolveInvitation('req', 'accept')).rejects.toThrow('邀请已处理')
  })
  it('列表方向、状态和分页全部通过 API 查询', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ items: [], total: 0 }))
    vi.stubGlobal('fetch', fetchMock)
    await buddyConnectionsApi.getInvitations({ direction: 'outgoing', status: 'pending', page: 2, pageSize: 12 })
    const url = new URL(fetchMock.mock.calls[0]![0], 'http://localhost')
    expect(url.searchParams.get('direction')).toBe('outgoing')
    expect(url.searchParams.get('status')).toBe('pending')
    expect(url.searchParams.get('page')).toBe('2')
  })
  it('解除关系接受 204，标记已读使用自己的通知资源路径', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(response({ id: 'notice', readAt: '2026-11-13T00:00:00+00:00' }))
    vi.stubGlobal('fetch', fetchMock)
    await buddyConnectionsApi.removeBuddy('relation')
    const notice = await buddyConnectionsApi.readNotification('notice')
    expect(fetchMock.mock.calls[0]![0]).toBe('/api/v1/buddies/relation')
    expect(fetchMock.mock.calls[0]![1].method).toBe('DELETE')
    expect(fetchMock.mock.calls[1]![1].method).toBe('PATCH')
    expect(notice.readAt).toBeTruthy()
  })
})
