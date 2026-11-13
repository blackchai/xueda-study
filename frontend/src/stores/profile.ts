import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

import { initialProfile } from '@/mocks/data'
import { matchingDataApi } from '@/services/matchingData'
import type { UserProfile } from '@/types/models'
import { cloneValue, loadStored, saveStored, STORAGE_KEYS } from '@/utils/storage'

export const useProfileStore = defineStore('profile', () => {
  const apiMode = import.meta.env.VITE_BUSINESS_DATA_MODE !== 'mock'
  function emptyProfile(): UserProfile {
    return {
      id: '', name: '同学', avatar: '学', school: '', major: '', bio: '',
      categories: [], tags: [], styles: [], timeSlots: [], dailyTargetMinutes: 180,
      publicProfile: false, allowInvites: false, checkinReminder: false, timezone: 'Asia/Shanghai',
    }
  }
  const profile = ref<UserProfile>(apiMode ? emptyProfile() : loadStored(STORAGE_KEYS.profile, initialProfile))
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const initialized = ref(false)
  let pending: Promise<void> | undefined
  let generation = 0

  watch(
    profile,
    (value) => { if (!apiMode) saveStored(STORAGE_KEYS.profile, value) },
    { deep: true },
  )

  async function initialize(force = false): Promise<void> {
    if (!apiMode || (initialized.value && !force)) return
    if (pending) return pending
    loading.value = true
    error.value = ''
    const requestGeneration = generation
    pending = matchingDataApi.getProfile().then((remote) => {
      if (generation !== requestGeneration) return
      profile.value = remote
      initialized.value = true
    }).catch((cause: unknown) => {
      if (generation === requestGeneration) error.value = cause instanceof Error ? cause.message : '学习档案加载失败'
      throw cause
    }).finally(() => {
      if (generation === requestGeneration) { loading.value = false; pending = undefined }
    })
    return pending
  }

  async function updateProfile(nextProfile: UserProfile): Promise<void> {
    if (!apiMode) { profile.value = cloneValue(nextProfile); return }
    saving.value = true
    const currentGeneration = generation
    try {
      const saved = await matchingDataApi.updateProfile(nextProfile)
      if (currentGeneration !== generation) return
      profile.value = saved
      initialized.value = true
    } finally {
      if (currentGeneration === generation) saving.value = false
    }
  }

  function clearAccountData(): void {
    if (!apiMode) return
    generation += 1
    pending = undefined
    profile.value = emptyProfile()
    initialized.value = false
    loading.value = false
    saving.value = false
    error.value = ''
  }

  function resetProfile(): void {
    if (apiMode) return
    profile.value = cloneValue(initialProfile)
  }

  return { profile, apiMode, loading, saving, error, initialized, initialize, updateProfile, clearAccountData, resetProfile }
})
