import { afterEach, describe, expect, it, vi } from 'vitest'
import { groupsApi } from './groups'

afterEach(() => vi.unstubAllGlobals())
const response = (data: unknown, status = 200) => new Response(JSON.stringify({ code: status >= 400 ? 'GROUP_FULL' : 0, message: status >= 400 ? '小组人数已满' : 'ok', data }), { status })

describe('小组真实接口与显式分享授权', () => {
  it('查询过滤和分页始终送往后端，不读取本地成员状态', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ items: [], total: 0, joinedTotal: 1 }))
    vi.stubGlobal('fetch', fetcher)
    const result = await groupsApi.list({ q: 'C++ & 学习', mine: true, category: '编程开发', page: 2 })
    const [path, options] = fetcher.mock.calls[0]!
    const url = new URL(path, 'http://localhost')
    expect(url.searchParams.get('q')).toBe('C++ & 学习')
    expect(url.searchParams.get('mine')).toBe('true')
    expect(url.searchParams.get('page')).toBe('2')
    expect(options.credentials).toBe('include')
    expect(result.joinedTotal).toBe(1)
  })
  it('审核型加入返回 pending，不伪装加入成功', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ state: 'pending', requestId: 'r1' }, 201)))
    expect((await groupsApi.join('g1')).state).toBe('pending')
  })
  it('满员冲突抛错，不写入本地假成员', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(null, 409)))
    await expect(groupsApi.join('g1')).rejects.toThrow('小组人数已满')
  })
  it('分享只提交现有打卡和明确授权，不发送他人身份或复制内容', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ groupId: 'g', shareContent: false }))
    vi.stubGlobal('fetch', fetcher)
    await groupsApi.share('record', 'g', false)
    expect(fetcher.mock.calls[0]![0]).toBe('/api/v1/checkins/record/groups/g')
    expect(JSON.parse(fetcher.mock.calls[0]![1].body)).toEqual({ shareContent: false })
  })
  it('撤回分享和退出使用资源 API 的 204 响应', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(null, { status: 204 })))
    vi.stubGlobal('fetch', fetcher)
    await groupsApi.unshare('record', 'g')
    await groupsApi.leave('g')
    expect(fetcher.mock.calls[0]![1].method).toBe('DELETE')
    expect(fetcher.mock.calls[1]![0]).toBe('/api/v1/groups/g/leave')
  })
  it('审批动作及排行榜周期使用指定资源，不信任前端传入身份', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(response({ items: [] })))
    vi.stubGlobal('fetch', fetcher)
    await groupsApi.resolve('g', 'r', 'approve')
    await groupsApi.rankings('g', 'days')
    expect(fetcher.mock.calls[0]![0]).toBe('/api/v1/groups/g/join-requests/r/approve')
    expect(fetcher.mock.calls[0]![1].body).toBeUndefined()
    expect(fetcher.mock.calls[1]![0]).toBe('/api/v1/groups/g/rankings?period=days')
  })
})
