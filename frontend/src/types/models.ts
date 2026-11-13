export const GOAL_CATEGORIES = [
  '考研',
  '考公',
  '四六级',
  '编程开发',
  '算法竞赛',
  '专业课程',
  '职业技能',
  '阅读写作',
] as const

export const STUDY_STYLES = ['安静自习', '番茄钟', '语音陪伴', '定期复盘', '任务互督', '独立学习', '相互监督', '共同讨论'] as const
export const STUDY_STAGES = ['入门', '基础', '强化', '冲刺'] as const
export const MOODS = ['状态极佳', '专注在线', '稳步推进', '有点疲惫'] as const

export type GoalCategory = (typeof GOAL_CATEGORIES)[number]
export type StudyStyle = (typeof STUDY_STYLES)[number]
export type StudyStage = (typeof STUDY_STAGES)[number]
export type Mood = (typeof MOODS)[number]
export type GoalStatus = '进行中' | '已完成' | '已暂停'
export type DayOfWeek = 1 | 2 | 3 | 4 | 5 | 6 | 7

export interface StudyTimeSlot {
  id: string
  day: DayOfWeek
  start: string
  end: string
}

export interface GoalTask {
  id: string
  title: string
  dueDate: string
  estimatedMinutes: number
  completed: boolean
}

export interface StudyGoal {
  id: string
  title: string
  description: string
  category: GoalCategory
  tags: string[]
  startDate: string
  targetDate: string
  status: GoalStatus
  color: string
  tasks: GoalTask[]
  createdAt: string
}

export interface Checkin {
  id: string
  date: string
  duration: number
  content: string
  mood: Mood
  goalId?: string
  createdAt: string
}

export interface UserProfile {
  id: string
  name: string
  avatar: string
  school: string
  major: string
  bio: string
  categories: GoalCategory[]
  tags: string[]
  styles: StudyStyle[]
  stage?: StudyStage
  timeSlots: StudyTimeSlot[]
  dailyTargetMinutes: number
  publicProfile: boolean
  allowInvites: boolean
  checkinReminder: boolean
  timezone?: 'Asia/Shanghai' | 'Asia/Hong_Kong'
}

export interface BuddyProfile {
  id: string
  name: string
  avatar: string
  school: string
  bio: string
  categories: GoalCategory[]
  tags: string[]
  styles: StudyStyle[]
  stage?: StudyStage
  timeSlots: StudyTimeSlot[]
  streakDays: number
  weeklyHours: number
  responseRate: number
  isOnline: boolean
}

export type BuddyRequestStatus = '待处理' | '已接受' | '已拒绝'

export interface BuddyRequest {
  id: string
  userId: string
  direction: '发出' | '收到'
  message: string
  status: BuddyRequestStatus
  createdAt: string
}

export interface GroupMember {
  id: string
  name: string
  avatar: string
  role: '组长' | '管理员' | '成员'
  weeklyMinutes: number
  streakDays: number
}

export interface StudyGroup {
  id: string
  name: string
  description: string
  category: GoalCategory
  tags: string[]
  memberCount: number
  maxMembers: number
  privacy: '公开加入' | '申请加入'
  createdBy: string
  isJoined: boolean
  weeklyGoalMinutes: number
  announcement: string
  members: GroupMember[]
  createdAt: string
}

export interface WeeklyStudyPoint {
  label: string
  date: string
  minutes: number
}

