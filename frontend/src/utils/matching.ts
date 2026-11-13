import type { GoalCategory, StudyStage, StudyStyle, StudyTimeSlot } from '@/types/models'

export interface MatchingProfile {
  id: string
  name: string
  categories: GoalCategory[]
  tags: string[]
  timeSlots: StudyTimeSlot[]
  styles: StudyStyle[]
  stage?: StudyStage
}

export interface MatchDimensions {
  goal: number
  time: number
  method: number
  level: number
}

export interface MatchResult {
  score: number
  dimensions: MatchDimensions
  reasons: string[]
  caveats: string[]
  overlapMinutes: number
}

const STAGE_ORDER: StudyStage[] = ['入门', '基础', '强化', '冲刺']

function roundScore(value: number): number {
  return Math.round(Math.max(0, Math.min(100, value)))
}

function normalise(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim().toLowerCase()).filter(Boolean))]
}

function intersection<T>(left: T[], right: T[]): T[] {
  const rightSet = new Set(right)
  return [...new Set(left)].filter((item) => rightSet.has(item))
}

function jaccard(left: string[], right: string[]): number | null {
  const a = normalise(left)
  const b = normalise(right)
  if (a.length === 0 || b.length === 0) return null

  const union = new Set([...a, ...b])
  return intersection(a, b).length / union.size
}

function comparableScore(parts: Array<{ value: number | null; weight: number }>): number {
  const available = parts.filter((part): part is { value: number; weight: number } => part.value !== null)
  if (available.length === 0) return 50

  const totalWeight = available.reduce((sum, part) => sum + part.weight, 0)
  return available.reduce((sum, part) => sum + part.value * (part.weight / totalWeight), 0)
}

export function calculateGoalSimilarity(a: MatchingProfile, b: MatchingProfile): number {
  const categorySimilarity = jaccard(a.categories, b.categories)
  const tagSimilarity = jaccard(a.tags, b.tags)
  return roundScore(
    comparableScore([
      { value: categorySimilarity === null ? null : categorySimilarity * 100, weight: 0.65 },
      { value: tagSimilarity === null ? null : tagSimilarity * 100, weight: 0.35 },
    ]),
  )
}

function timeToMinutes(time: string): number {
  const [hourText = '0', minuteText = '0'] = time.split(':')
  return Number(hourText) * 60 + Number(minuteText)
}

interface Interval {
  start: number
  end: number
}

function mergeIntervals(slots: StudyTimeSlot[], day: number): Interval[] {
  const intervals = slots
    .filter((slot) => slot.day === day)
    .map((slot) => ({ start: timeToMinutes(slot.start), end: timeToMinutes(slot.end) }))
    .filter((slot) => slot.end > slot.start)
    .sort((a, b) => a.start - b.start)

  const merged: Interval[] = []
  for (const interval of intervals) {
    const last = merged.at(-1)
    if (!last || interval.start > last.end) {
      merged.push({ ...interval })
    } else {
      last.end = Math.max(last.end, interval.end)
    }
  }
  return merged
}

function sumIntervals(intervals: Interval[]): number {
  return intervals.reduce((sum, interval) => sum + interval.end - interval.start, 0)
}

export function calculateTimeSimilarity(
  leftSlots: StudyTimeSlot[],
  rightSlots: StudyTimeSlot[],
): { score: number; overlapMinutes: number } {
  if (leftSlots.length === 0 || rightSlots.length === 0) {
    return { score: 50, overlapMinutes: 0 }
  }

  let leftTotal = 0
  let rightTotal = 0
  let overlapMinutes = 0

  for (let day = 1; day <= 7; day += 1) {
    const left = mergeIntervals(leftSlots, day)
    const right = mergeIntervals(rightSlots, day)
    leftTotal += sumIntervals(left)
    rightTotal += sumIntervals(right)

    for (const a of left) {
      for (const b of right) {
        overlapMinutes += Math.max(0, Math.min(a.end, b.end) - Math.max(a.start, b.start))
      }
    }
  }

  const comparableMinutes = Math.min(leftTotal, rightTotal)
  return {
    score: comparableMinutes === 0 ? 0 : roundScore((overlapMinutes / comparableMinutes) * 100),
    overlapMinutes,
  }
}

export function calculateMethodSimilarity(left: StudyStyle[], right: StudyStyle[]): number {
  const similarity = jaccard(left, right)
  return similarity === null ? 50 : roundScore(similarity * 100)
}

export function calculateLevelSimilarity(left?: StudyStage, right?: StudyStage): number {
  if (!left || !right) return 50
  const distance = Math.abs(STAGE_ORDER.indexOf(left) - STAGE_ORDER.indexOf(right))
  return [100, 70, 40, 10][distance] ?? 10
}

function formatHours(minutes: number): string {
  const hours = minutes / 60
  return Number.isInteger(hours) ? `${hours} 小时` : `${hours.toFixed(1)} 小时`
}

export function calculateMatch(a: MatchingProfile, b: MatchingProfile): MatchResult {
  const goal = calculateGoalSimilarity(a, b)
  const timeResult = calculateTimeSimilarity(a.timeSlots, b.timeSlots)
  const method = calculateMethodSimilarity(a.styles, b.styles)
  const level = calculateLevelSimilarity(a.stage, b.stage)
  const score = roundScore(goal * 0.4 + timeResult.score * 0.35 + method * 0.15 + level * 0.1)

  const sharedCategories = intersection(a.categories, b.categories)
  const sharedTags = intersection(normalise(a.tags), normalise(b.tags))
  const sharedStyles = intersection(a.styles, b.styles)
  const reasons: string[] = []
  const caveats: string[] = []

  if (sharedCategories.length > 0) reasons.push(`共同方向：${sharedCategories.slice(0, 2).join('、')}`)
  if (sharedTags.length > 0) reasons.push(`目标标签契合：${sharedTags.slice(0, 2).join('、')}`)
  if (timeResult.overlapMinutes > 0) reasons.push(`每周可共同学习约 ${formatHours(timeResult.overlapMinutes)}`)
  if (sharedStyles.length > 0) reasons.push(`都偏好${sharedStyles.slice(0, 2).join('、')}`)
  if (a.stage && b.stage && a.stage === b.stage) reasons.push(`同处${a.stage}阶段`)

  if (a.timeSlots.length === 0 || b.timeSlots.length === 0) caveats.push('一方尚未完善学习时段，时间分按中性值计算')
  if (a.styles.length === 0 || b.styles.length === 0) caveats.push('一方尚未设置学习方式，方式分按中性值计算')
  if (!a.stage || !b.stage) caveats.push('一方尚未设置学习阶段，阶段分按中性值计算')
  if (timeResult.overlapMinutes === 0 && a.timeSlots.length > 0 && b.timeSlots.length > 0) {
    caveats.push('当前可用时段没有重合')
  }

  if (reasons.length === 0) reasons.push('资料仍在完善，可先从共同目标聊起')

  return {
    score,
    dimensions: { goal, time: timeResult.score, method, level },
    reasons: reasons.slice(0, 3),
    caveats,
    overlapMinutes: timeResult.overlapMinutes,
  }
}

export function rankMatches<T extends MatchingProfile>(viewer: MatchingProfile, candidates: T[]): Array<T & MatchResult> {
  return candidates
    .map((candidate) => ({ ...candidate, ...calculateMatch(viewer, candidate) }))
    .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, 'zh-CN'))
}

