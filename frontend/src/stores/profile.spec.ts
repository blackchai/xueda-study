import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { initialProfile } from '@/mocks/data'
import { matchingDataApi } from '@/services/matchingData'
import { useProfileStore } from './profile'

vi.mock('@/services/matchingData', () => ({
  matchingDataApi: { getProfile: vi.fn(), updateProfile: vi.fn() },
}))

describe('真实学习档案状态', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_BUSINESS_DATA_MODE', 'api')
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  afterEach(() => vi.unstubAllEnvs())

  it('新账号从服务端加载，默认没有 Mock 资料并关闭公开推荐', async () => {
    const store = useProfileStore()
    expect(store.profile.categories).toEqual([])
    expect(store.profile.publicProfile).toBe(false)
    vi.mocked(matchingDataApi.getProfile).mockResolvedValue({ ...initialProfile, name: '真实昵称' })
    await Promise.all([store.initialize(), store.initialize()])
    expect(matchingDataApi.getProfile).toHaveBeenCalledTimes(1)
    expect(store.profile.name).toBe('真实昵称')
    expect(store.initialized).toBe(true)
  })

  it('保存失败不会覆盖已经加载的档案，且允许重试', async () => {
    const store = useProfileStore()
    vi.mocked(matchingDataApi.getProfile).mockResolvedValue({ ...initialProfile, name: '已保存' })
    await store.initialize()
    vi.mocked(matchingDataApi.updateProfile).mockRejectedValue(new Error('网络失败'))
    await expect(store.updateProfile({ ...store.profile, name: '未保存' })).rejects.toThrow('网络失败')
    expect(store.profile.name).toBe('已保存')
    expect(store.saving).toBe(false)
    vi.mocked(matchingDataApi.updateProfile).mockResolvedValue({ ...initialProfile, name: '重试保存' })
    await store.updateProfile({ ...store.profile, name: '重试保存' })
    expect(store.profile.name).toBe('重试保存')
  })

  it('切换账号后，旧账号的延迟响应不能恢复私人档案', async () => {
    const store = useProfileStore()
    let resolveOld!: (value: typeof initialProfile) => void
    vi.mocked(matchingDataApi.getProfile).mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve }))
    const oldLoad = store.initialize()
    store.clearAccountData()
    vi.mocked(matchingDataApi.getProfile).mockResolvedValueOnce({ ...initialProfile, name: 'B账号' })
    await store.initialize()
    resolveOld({ ...initialProfile, name: 'A账号' })
    await oldLoad
    expect(store.profile.name).toBe('B账号')
  })

  it('加载失败暴露错误且能够重新请求', async () => {
    const store = useProfileStore()
    vi.mocked(matchingDataApi.getProfile).mockRejectedValueOnce(new Error('请先登录'))
    await expect(store.initialize()).rejects.toThrow('请先登录')
    expect(store.error).toBe('请先登录')
    expect(store.loading).toBe(false)
    vi.mocked(matchingDataApi.getProfile).mockResolvedValueOnce(initialProfile)
    await store.initialize()
    expect(store.error).toBe('')
  })
})
