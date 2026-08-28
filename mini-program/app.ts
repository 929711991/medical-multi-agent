import globalConfig from './service/config'

App({ globalData: { apiBase: globalConfig.host, version: globalConfig.version } })
