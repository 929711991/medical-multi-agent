import site from './site.json'

type SiteEnvironment = keyof typeof site

const requestedEnvironment = String(import.meta.env.VITE_APP_ENV || 'dev')
const environment: SiteEnvironment = requestedEnvironment in site
  ? requestedEnvironment as SiteEnvironment
  : 'dev'
const selected = site[environment]
const configuredTimeout = Number(import.meta.env.VITE_REQUEST_TIMEOUT)

const globalConfig = Object.freeze({
  environment,
  name: selected.name,
  host: String(import.meta.env.VITE_API_BASE_URL || selected.host).replace(/\/+$/, ''),
  healthUrl: String(import.meta.env.VITE_HEALTH_URL || selected.healthUrl),
  requestTimeout: Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : selected.requestTimeout,
  tokenStorageKey: selected.tokenStorageKey,
  version: selected.version,
})

export default globalConfig
