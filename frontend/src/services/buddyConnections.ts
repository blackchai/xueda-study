import { request, requestNoContent } from './httpClient'
import type { PageResult } from '@/types/api'
import type { BuddyInvitation, BuddyNotification, BuddyRelation, InvitationAction, InvitationFilters, InvitationPage, ListOptions, NotificationPage } from '@/types/buddies'

function query(values: object): string {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  return params.toString()
}

export const buddyConnectionsApi = {
  async sendInvitation(recipientId: string, message: string): Promise<BuddyInvitation> {
    return (await request<BuddyInvitation>('/buddy-requests', {
      method: 'POST', body: JSON.stringify({ recipientId, message }),
    })).data
  },
  async getInvitations(filters: InvitationFilters = {}): Promise<InvitationPage> {
    return (await request<InvitationPage>(`/buddy-requests?${query(filters)}`)).data
  },
  async resolveInvitation(id: string, action: InvitationAction): Promise<BuddyInvitation> {
    return (await request<BuddyInvitation>(`/buddy-requests/${id}/${action}`, { method: 'POST' })).data
  },
  async getBuddies(options: ListOptions = {}): Promise<PageResult<BuddyRelation>> {
    return (await request<PageResult<BuddyRelation>>(`/buddies?${query(options)}`)).data
  },
  async removeBuddy(id: string): Promise<void> {
    await requestNoContent(`/buddies/${id}`, { method: 'DELETE' })
  },
  async getNotifications(options: ListOptions & { unreadOnly?: boolean } = {}): Promise<NotificationPage> {
    return (await request<NotificationPage>(`/notifications?${query(options)}`)).data
  },
  async readNotification(id: string): Promise<BuddyNotification> {
    return (await request<BuddyNotification>(`/notifications/${id}/read`, { method: 'PATCH' })).data
  },
  async unreadCount(): Promise<{ unreadCount: number }> {
    return (await request<{ unreadCount: number }>('/notifications/unread-count')).data
  },
  async readAllNotifications(): Promise<{ updatedCount: number; unreadCount: number }> {
    return (await request<{ updatedCount: number; unreadCount: number }>('/notifications/read-all', { method: 'PATCH' })).data
  },
}
