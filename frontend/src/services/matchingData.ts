import { request } from './httpClient'
import type { UserProfile } from '@/types/models'
import type { ProfileResponse, RecommendationFilters, RecommendationPage } from '@/types/matching'

function toProfile(remote: ProfileResponse): UserProfile {
  return { ...remote, stage: remote.stage ?? undefined, allowInvites: remote.allowInvites ?? false, checkinReminder: false }
}

export const matchingDataApi = {
  async getProfile(): Promise<UserProfile> {
    return toProfile((await request<ProfileResponse>('/profiles/me')).data)
  },

  async updateProfile(profile: UserProfile): Promise<UserProfile> {
    const { name, school, major, bio, categories, tags, styles, stage, dailyTargetMinutes, publicProfile, allowInvites } = profile
    const payload = {
      name, school, major, bio, categories, tags, styles, stage: stage ?? null,
      dailyTargetMinutes, publicProfile, allowInvites, timezone: profile.timezone ?? 'Asia/Shanghai',
      timeSlots: profile.timeSlots.map(({ day, start, end }) => ({ day, start, end })),
    }
    return toProfile((await request<ProfileResponse>('/profiles/me', {
      method: 'PUT', body: JSON.stringify(payload),
    })).data)
  },

  async getRecommendations(filters: RecommendationFilters = {}): Promise<RecommendationPage> {
    const query = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') query.set(key, String(value))
    })
    return (await request<RecommendationPage>(`/buddies/recommendations?${query.toString()}`)).data
  },
}
