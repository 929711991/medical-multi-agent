import globalConfig from '../service/config'
import { httpGet } from '../service/http'

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  service: string
  mysql: string
  checkpoint: string
  mcp: string
  llm: string
  rag_enabled: boolean
  rag_required: boolean
  rag_ready: boolean
  redis: string
  redis_vector_ready: boolean
  embedding_ready: boolean
  knowledge_documents: number
}

export async function getHealth(): Promise<HealthStatus> {
  /** 获取后端依赖服务的聚合健康状态。 */
  return httpGet<HealthStatus>(globalConfig.healthUrl, undefined, { baseURL: '/' })
}
