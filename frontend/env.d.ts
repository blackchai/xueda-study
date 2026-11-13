/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_BUSINESS_DATA_MODE?: 'api' | 'mock'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
