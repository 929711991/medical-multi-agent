import axios from 'axios'

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
  milvus: string
  knowledge_documents: number
}

export async function getHealth(): Promise<HealthStatus> {
  return (await axios.get<HealthStatus>('/health', { withCredentials: true, timeout: 45_000 })).data
}
