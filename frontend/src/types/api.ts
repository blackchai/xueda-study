import type {
  Checkin,
  StudyGoal,
} from './models'

export interface ApiResponse<T> {
  code: number | string
  message: string
  data: T
  requestId?: string
  request_id?: string
}

export interface PageResult<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

export interface LoginPayload {
  account: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  confirmPassword: string
}

export interface AuthenticatedUser {
  userId: string
  username?: string
  email?: string
  displayName: string
  avatarUrl?: string
  onboardingCompleted: boolean
}

export interface StudyMateApi {
  login(payload: LoginPayload): Promise<ApiResponse<AuthenticatedUser>>
  register(payload: RegisterPayload): Promise<ApiResponse<AuthenticatedUser>>
  getGoals(): Promise<ApiResponse<StudyGoal[]>>
  getCheckins(): Promise<ApiResponse<Checkin[]>>
}
