export const STORAGE_KEYS = {
  study: 'studymate.prototype.study.v1',
  social: 'studymate.prototype.social.v1',
  profile: 'studymate.prototype.profile.v1',
} as const

export function cloneValue<T>(value: T): T {
  try {
    return structuredClone(value)
  } catch {
    // Vue reactive proxies cannot be passed to structuredClone directly.
    // Prototype state is intentionally JSON-serialisable, so this is a safe fallback.
    return JSON.parse(JSON.stringify(value)) as T
  }
}

export function loadStored<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return cloneValue(fallback)

  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : cloneValue(fallback)
  } catch {
    return cloneValue(fallback)
  }
}

export function saveStored<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Prototype data persistence is best-effort. The UI remains usable in memory.
  }
}

export function createId(prefix: string): string {
  const randomPart = Math.random().toString(36).slice(2, 9)
  return `${prefix}_${Date.now().toString(36)}_${randomPart}`
}
