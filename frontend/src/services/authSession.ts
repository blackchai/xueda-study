import { request, requestNoContent } from '@/services/httpClient'
import type { AuthenticatedUser } from '@/types/api'

let cachedUser: AuthenticatedUser | undefined
let pendingRequest: Promise<AuthenticatedUser> | undefined
let revision = 0

export async function getAuthenticatedUser(force = false): Promise<AuthenticatedUser> {
  if (!force && cachedUser) return cachedUser
  if (!force && pendingRequest) return pendingRequest

  const ticket = revision
  const current = request<AuthenticatedUser>('/auth/me')
    .then((response) => {
      if (ticket !== revision) throw new Error('登录状态已改变，请重新登录')
      cachedUser = response.data
      return response.data
    })
    .finally(() => {
      if (pendingRequest === current) pendingRequest = undefined
    })
  pendingRequest = current
  return current
}

export function clearAuthenticatedUser(): void {
  revision++
  cachedUser = undefined
  pendingRequest = undefined
}

export function setAuthenticatedUser(user: AuthenticatedUser): void {
  revision++
  cachedUser = user
  pendingRequest = undefined
}

export async function logoutAuthenticatedUser(): Promise<void> {
  try {
    await requestNoContent('/auth/logout', { method: 'POST' })
  } finally {
    clearAuthenticatedUser()
  }
}
