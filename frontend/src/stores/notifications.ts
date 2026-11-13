import { defineStore } from 'pinia'
import { ref } from 'vue'
import { buddyConnectionsApi } from '@/services/buddyConnections'
import { ApiError } from '@/services/httpClient'

/** Memory only. One shared count request; old-account responses cannot refill state. */
export const useNotificationStore = defineStore('notifications', () => {
  const unreadCount = ref(0), error = ref(''), expired = ref(false)
  let revision = 0, lastUpdated = 0
  let pending: Promise<void> | undefined
  function acceptCount(value: number): void { revision++; unreadCount.value = value; error.value = ''; lastUpdated = Date.now() }
  function reset(): void { revision++; pending = undefined; lastUpdated = 0; unreadCount.value = 0; error.value = ''; expired.value = false }
  function refreshCount(force = false): Promise<void> {
    if (pending) return pending
    if (!force && Date.now() - lastUpdated < 5000) return Promise.resolve()
    const ticket = revision
    const current = buddyConnectionsApi.unreadCount().then(result => {
      if (ticket === revision) acceptCount(result.unreadCount)
    }).catch((cause: unknown) => {
      if (ticket !== revision) return
      if (cause instanceof ApiError && cause.status === 401) { reset(); expired.value = true }
      else error.value = cause instanceof Error ? cause.message : '通知同步失败，请重试'
    }).finally(() => { if (pending === current) pending = undefined })
    pending = current
    return current
  }
  return { unreadCount, error, expired, acceptCount, reset, refreshCount }
})
