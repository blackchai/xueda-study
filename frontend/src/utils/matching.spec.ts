import { describe, expect, it } from 'vitest'

import { buddyCandidates, initialProfile } from '@/mocks/data'

import type { MatchingProfile } from './matching'
import {
  calculateMatch,
  calculateTimeSimilarity,
  rankMatches,
} from './matching'

const base: MatchingProfile = {
  id: 'viewer',
  name: '测试用户',
  categories: ['考研'],
  tags: ['数学', '英语'],
  styles: ['番茄钟', '任务互督'],
  stage: '强化',
  timeSlots: [
    { id: 'a', day: 1, start: '19:00', end: '21:00' },
    { id: 'b', day: 3, start: '19:00', end: '21:00' },
  ],
}

describe('学习搭子匹配算法', () => {
  it('完全一致的资料得到 100 分', () => {
    const result = calculateMatch(base, { ...base, id: 'same', name: '同伴' })
    expect(result.score).toBe(100)
    expect(result.dimensions).toEqual({ goal: 100, time: 100, method: 100, level: 100 })
  })

  it('已设置但完全不重合的时段得到 0 分', () => {
    const result = calculateTimeSimilarity(base.timeSlots, [
      { id: 'c', day: 2, start: '08:00', end: '10:00' },
    ])
    expect(result).toEqual({ score: 0, overlapMinutes: 0 })
  })

  it('缺失偏好使用 50 分中性值并给出说明', () => {
    const incomplete: MatchingProfile = {
      id: 'incomplete',
      name: '资料未完善',
      categories: [],
      tags: [],
      styles: [],
      timeSlots: [],
    }
    const result = calculateMatch(base, incomplete)
    expect(result.dimensions).toEqual({ goal: 50, time: 50, method: 50, level: 50 })
    expect(result.score).toBe(50)
    expect(result.caveats.length).toBeGreaterThanOrEqual(3)
  })

  it('推荐列表按总分从高到低排列', () => {
    const close = { ...base, id: 'close', name: '高度匹配' }
    const distant: MatchingProfile = {
      id: 'distant',
      name: '低度匹配',
      categories: ['编程开发'],
      tags: ['前端'],
      styles: ['语音陪伴'],
      stage: '入门',
      timeSlots: [{ id: 'd', day: 7, start: '08:00', end: '09:00' }],
    }
    const results = rankMatches(base, [distant, close])
    expect(results.map((item) => item.id)).toEqual(['close', 'distant'])
    expect(results[0]?.score).toBeGreaterThan(results[1]?.score ?? 0)
  })

  it('模拟候选人的结果与产品文档一致', () => {
    const results = rankMatches(initialProfile, buddyCandidates)
    expect(results.map((item) => [item.name, item.score])).toEqual([
      ['陈知行', 92],
      ['苏念', 56],
      ['周屿', 32],
      ['罗一然', 30],
      ['唐可', 14],
    ])
  })
})
