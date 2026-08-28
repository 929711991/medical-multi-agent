import site from './site.json'

export type SiteEnvironment = keyof typeof site

// 微信小程序没有 Vite 环境变量；联调/发布时只需在这里切换环境并维护 site.json。
const environment: SiteEnvironment = 'dev'
const selected = site[environment]

const globalConfig = Object.freeze({
  environment,
  name: selected.name,
  host: selected.host.replace(/\/+$/, ''),
  requestTimeout: selected.requestTimeout,
  tokenStorageKey: selected.tokenStorageKey,
  version: selected.version,
})

export default globalConfig
