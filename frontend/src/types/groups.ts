import type { PageResult } from './api'
import type { GoalCategory } from './models'

export type GroupRole = 'owner' | 'member'
export type JoinStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'
export type RankingPeriod = 'day' | 'week' | 'month' | 'days'
export interface GroupWritePayload {
  name: string
  category: GoalCategory
  description: string
  maxMembers: number
  requiresApproval: boolean
  tags: string[]
  announcement: string
}
export interface GroupSummary extends Omit<GroupWritePayload, 'announcement'> {
  id: string
  ownerName: string
  memberCount: number
  myRole: GroupRole | null
  isJoined: boolean
  joinRequest: { id: string; status: JoinStatus } | null
  createdAt: string
}
export interface GroupPage extends PageResult<GroupSummary> { joinedTotal: number }
export interface GroupStatistics {
  todayMembers: number
  totalMinutes: number
  weekMinutes: number
  weekMembers: number
  weekStart: string
  weekEnd: string
  weekDays: Array<{ date: string; minutes: number; memberCount: number; recordCount: number }>
  asOfDate: string
  timezone: string
}
export interface GroupGoalWrite { title: string; startDate: string; endDate: string; targetMinutes: number }
export interface GroupGoal extends GroupGoalWrite {
  id: string
  myMinutes: number
  myDays: number
  progress: number
  updatedAt: string
}
export interface GroupDetail extends GroupSummary { announcement: string; statistics: GroupStatistics; goal: GroupGoal | null; myJoinedAt: string }
export interface GroupMember {
  userId: string
  name: string
  avatar: string
  role: GroupRole
  joinedAt: string
  isMe: boolean
}
export interface JoinRequest { id: string; userId: string; name: string; status: JoinStatus; createdAt: string }
export interface GroupRank {
  rank: number
  userId: string
  name: string
  avatar: string
  role: GroupRole
  minutes: number
  days: number
  records: number
  isMe: boolean
}
export interface RankingResult { items: GroupRank[]; period: RankingPeriod; startDate: string; endDate: string; asOfDate: string; timezone: string }
export interface SharedCheckin {
  checkinId: string
  date: string
  duration: number
  content: string | null
  shareContent: boolean
  sharedAt: string
  user: { id: string; name: string; avatar: string }
}
export interface CheckinGroupShare { groupId: string; groupName: string; shareContent: boolean; sharedAt: string }
