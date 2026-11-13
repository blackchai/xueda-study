import { request, requestNoContent } from './httpClient'
import type { PageResult } from '@/types/api'
import type { CheckinGroupShare, GroupDetail, GroupGoal, GroupGoalWrite, GroupMember, GroupPage, GroupSummary, GroupWritePayload, JoinRequest, JoinStatus, RankingPeriod, RankingResult, SharedCheckin } from '@/types/groups'
import type { GoalCategory } from '@/types/models'

function query(options: object): string {
  const params = new URLSearchParams()
  Object.entries(options).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)) })
  return params.toString()
}
type ListOptions = { page?: number; pageSize?: number }
export const groupsApi = {
  async list(options: ListOptions & { q?: string; category?: GoalCategory; mine?: boolean } = {}): Promise<GroupPage> {
    return (await request<GroupPage>(`/groups?${query(options)}`)).data
  },
  async create(payload: GroupWritePayload): Promise<GroupSummary> {
    return (await request<GroupSummary>('/groups', { method: 'POST', body: JSON.stringify(payload) })).data
  },
  async preview(id: string): Promise<GroupSummary> { return (await request<GroupSummary>(`/groups/${id}/preview`)).data },
  async detail(id: string): Promise<GroupDetail> { return (await request<GroupDetail>(`/groups/${id}`)).data },
  async update(id: string, payload: GroupWritePayload): Promise<GroupSummary> {
    return (await request<GroupSummary>(`/groups/${id}`, { method: 'PUT', body: JSON.stringify(payload) })).data
  },
  async join(id: string): Promise<{ state: 'joined' | 'pending'; requestId: string | null }> {
    return (await request<{ state: 'joined' | 'pending'; requestId: string | null }>(`/groups/${id}/join`, { method: 'POST' })).data
  },
  async leave(id: string): Promise<void> { await requestNoContent(`/groups/${id}/leave`, { method: 'POST' }) },
  async dissolve(id: string): Promise<void> { await requestNoContent(`/groups/${id}`, { method: 'DELETE' }) },
  async members(id: string): Promise<{ items: GroupMember[] }> { return (await request<{ items: GroupMember[] }>(`/groups/${id}/members`)).data },
  async removeMember(id: string, userId: string): Promise<void> { await requestNoContent(`/groups/${id}/members/${userId}`, { method: 'DELETE' }) },
  async transfer(id: string, newOwnerId: string): Promise<GroupSummary> {
    return (await request<GroupSummary>(`/groups/${id}/transfer`, { method: 'POST', body: JSON.stringify({ newOwnerId }) })).data
  },
  async requests(id: string, options: ListOptions & { status?: JoinStatus } = {}): Promise<PageResult<JoinRequest>> {
    return (await request<PageResult<JoinRequest>>(`/groups/${id}/join-requests?${query(options)}`)).data
  },
  async resolve(id: string, requestId: string, action: 'approve' | 'reject' | 'cancel'): Promise<{ id: string; status: JoinStatus }> {
    return (await request<{ id: string; status: JoinStatus }>(`/groups/${id}/join-requests/${requestId}/${action}`, { method: 'POST' })).data
  },
  async setGoal(id: string, payload: GroupGoalWrite): Promise<GroupGoal> {
    return (await request<GroupGoal>(`/groups/${id}/goal`, { method: 'PUT', body: JSON.stringify(payload) })).data
  },
  async rankings(id: string, period: RankingPeriod = 'week'): Promise<RankingResult> {
    return (await request<RankingResult>(`/groups/${id}/rankings?${query({ period })}`)).data
  },
  async feed(id: string, options: ListOptions = {}): Promise<PageResult<SharedCheckin>> {
    return (await request<PageResult<SharedCheckin>>(`/groups/${id}/checkins?${query(options)}`)).data
  },
  async shares(checkinId: string): Promise<{ items: CheckinGroupShare[] }> {
    return (await request<{ items: CheckinGroupShare[] }>(`/checkins/${checkinId}/group-shares`)).data
  },
  async share(checkinId: string, groupId: string, shareContent: boolean): Promise<Omit<CheckinGroupShare, 'groupName'>> {
    return (await request<Omit<CheckinGroupShare, 'groupName'>>(`/checkins/${checkinId}/groups/${groupId}`, { method: 'PUT', body: JSON.stringify({ shareContent }) })).data
  },
  async unshare(checkinId: string, groupId: string): Promise<void> {
    await requestNoContent(`/checkins/${checkinId}/groups/${groupId}`, { method: 'DELETE' })
  },
}
