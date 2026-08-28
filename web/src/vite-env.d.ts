/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_ENV?: 'dev' | 'self' | 'prod'
  readonly VITE_API_BASE_URL?: string
  readonly VITE_HEALTH_URL?: string
  readonly VITE_REQUEST_TIMEOUT?: string
  readonly VITE_FEATURE_RAG?: string
  readonly VITE_DEV_MODE?: string
}
