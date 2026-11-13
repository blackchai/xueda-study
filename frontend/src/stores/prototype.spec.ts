import dayjs from 'dayjs'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useProfileStore } from './profile'
import { useStudyStore } from './study'

describe('第一阶段原型状态交互', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_BUSINESS_DATA_MODE', 'mock')
    setActivePinia(createPinia())
  })

  afterEach(() => vi.unstubAllEnvs())

  it('任务勾选会更新目标进度', () => {
    const store = useStudyStore()
    const goal = store.goals.find((item) => item.id === 'goal_postgrad')
    if (!goal) throw new Error('缺少考研目标 Mock 数据')

    expect(store.goalProgress(goal)).toBe(40)
    store.toggleTask(goal.id, 'task_1')
    expect(store.goalProgress(goal)).toBe(60)
  })

  it('支持目标创建、修改、添加任务和删除', async () => {
    const store = useStudyStore()
    const goalId = await store.addGoal({
      title: '测试目标',
      description: '验证原型状态动作',
      category: '专业课程',
      tags: ['测试'],
      startDate: dayjs().format('YYYY-MM-DD'),
      targetDate: dayjs().add(30, 'day').format('YYYY-MM-DD'),
      status: '进行中',
      color: '#5b5ce2',
      tasks: [],
    })

    store.updateGoal(goalId, { title: '已修改目标' })
    store.addTask(goalId, {
      title: '第一项任务',
      dueDate: dayjs().format('YYYY-MM-DD'),
      estimatedMinutes: 45,
      completed: false,
    })

    const goal = store.goals.find((item) => item.id === goalId)
    expect(goal?.title).toBe('已修改目标')
    expect(goal?.tasks).toHaveLength(1)

    store.removeGoal(goalId)
    expect(store.goals.some((item) => item.id === goalId)).toBe(false)
  })

  it('提交打卡会增加累计学习时长', () => {
    const store = useStudyStore()
    const before = store.totalMinutes
    store.addCheckin({
      date: dayjs().format('YYYY-MM-DD'),
      duration: 75,
      content: '完成业务状态测试',
      mood: '专注在线',
      goalId: 'goal_postgrad',
    })
    expect(store.totalMinutes).toBe(before + 75)
    expect(store.checkins[0]?.content).toBe('完成业务状态测试')
  })

  it('个人资料可以修改并恢复初始值', async () => {
    const store = useProfileStore()
    await store.updateProfile({ ...store.profile, name: '测试昵称', avatar: '测' })
    expect(store.profile.name).toBe('测试昵称')
    store.resetProfile()
    expect(store.profile.name).toBe('林小满')
  })
})
