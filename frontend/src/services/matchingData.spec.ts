import { afterEach, describe, expect, it, vi } from 'vitest'

import { initialProfile } from '@/mocks/data'
import { matchingDataApi } from './matchingData'

afterEach(() => vi.unstubAllGlobals())

function successfulResponse(data: unknown): Response {
  return new Response(JSON.stringify({ code: 0, message: 'ok', data }), { status: 200 })
}

describe('真实档案与推荐 API', () => {
  it('保存只发送可编辑字段和真实邀请开关，不发送用户 ID 或时段 ID', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse(initialProfile))
    vi.stubGlobal('fetch', fetchMock)
    await matchingDataApi.updateProfile(initialProfile)
    const [url, options] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/profiles/me')
    expect(options.credentials).toBe('include')
    const body = JSON.parse(options.body)
    expect(body).not.toHaveProperty('id')
    expect(body.allowInvites).toBe(initialProfile.allowInvites)
    expect(body.timeSlots[0]).not.toHaveProperty('id')
    expect(body.tags).toEqual(initialProfile.tags)
  })

  it('筛选参数保留 C++ 字符并把分页交给后端', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({ items: [], total: 0, page: 2, pageSize: 12 }))
    vi.stubGlobal('fetch', fetchMock)
    await matchingDataApi.getRecommendations({ category: '编程开发', q: 'C++', day: 1, period: 'evening', page: 2 })
    const url = new URL(fetchMock.mock.calls[0]![0], 'http://localhost')
    expect(url.searchParams.get('q')).toBe('C++')
    expect(url.searchParams.get('page')).toBe('2')
    expect(url.searchParams.get('category')).toBe('编程开发')
  })

  it('不会把会话失效伪装成空推荐', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: 'UNAUTHENTICATED', message: '请先登录', data: null,
    }), { status: 401 })))
    await expect(matchingDataApi.getRecommendations()).rejects.toThrow('请先登录')
  })
})
