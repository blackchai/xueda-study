import type { PageResult } from './api'
import type { BuddyConnection, PublicBuddyProfile } from './matching'

export type InvitationStatus = 'pending' | 'accepted' | 'rejected' | 'cancelled'
export type InvitationAction = 'accept' | 'reject' | 'cancel'
export type ConnectionTab = 'incoming' | 'outgoing' | 'mine' | 'notifications'

export interface BuddyInvitation {
  id: string
  senderId: string
  recipientId: string
  direction: 'incoming' | 'outgoing'
  status: InvitationStatus
  message: string
  createdAt: string
  updatedAt: string
  resolvedAt: string | null
  peer: PublicBuddyProfile
  connection: BuddyConnection
}

export interface BuddyRelation {
  id: string
  createdAt: string
  peer: PublicBuddyProfile
}

export interface BuddyNotification {
  id: string
  kind: 'buddy_request_received' | 'buddy_request_accepted' | 'buddy_request_rejected' | 'buddy_relation_removed' | 'group_join_requested' | 'group_join_approved' | 'group_join_rejected' | 'group_member_removed'
  title: string
  actor: { id: string; name: string } | null
  requestId: string | null
  relationId: string | null
  groupId: string | null
  groupRequestId: string | null
  groupEventId: string | null
  groupName: string | null
  href: string
  createdAt: string
  readAt: string | null
}

export interface ListOptions { page?: number; pageSize?: number }
export interface InvitationFilters extends ListOptions {
  direction?: 'incoming' | 'outgoing'
  status?: InvitationStatus
}
export interface InvitationPage extends PageResult<BuddyInvitation> { pendingCount: number }
export interface NotificationPage extends PageResult<BuddyNotification> { unreadCount: number }
