import type { DayOfWeek, GoalCategory, StudyStage, StudyStyle, StudyTimeSlot, UserProfile } from './models'
import type { MatchResult } from '@/utils/matching'
import type { PageResult } from './api'

export interface BuddyConnection {
  status: 'none' | 'outgoing_pending' | 'incoming_pending' | 'connected'
  requestId?: string
  relationId?: string
}

export interface PublicBuddyProfile {
  id: string
  name: string
  avatar: string
  categories: GoalCategory[]
  tags: string[]
  styles: StudyStyle[]
  stage: StudyStage | null
  timeSlots: Array<Omit<StudyTimeSlot, 'id'>>
  timezone: string
  allowInvites: boolean
  profileVisible?: boolean
}

export interface RecommendedBuddy extends PublicBuddyProfile, MatchResult {
  connection: BuddyConnection
}

export type ProfileResponse = Omit<UserProfile, 'stage' | 'checkinReminder'> & {
  stage: StudyStage | null
}

export interface RecommendationFilters {
  category?: GoalCategory
  period?: 'morning' | 'daytime' | 'evening'
  day?: DayOfWeek
  start?: string
  end?: string
  overlapOnly?: boolean
  q?: string
  page?: number
  pageSize?: number
}

export interface RecommendationPage extends PageResult<RecommendedBuddy> {
  timezone: string
  algorithmVersion: string
}
