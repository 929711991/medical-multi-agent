import { httpGet } from '../service/http'

export const ragEnabled = import.meta.env.VITE_FEATURE_RAG !== 'false'

export interface KnowledgeStatus {
  rag_enabled: boolean
  rag_required: boolean
  rag_ready: boolean
  redis: string
  collection: string
  embedding_model: string | null
  knowledge_documents: number
  message: string | null
}

export interface KnowledgeDocument {
  id: string
  title: string
  source: string
  source_type: string
  version: string | null
  published_at: string | null
  checksum: string
  status: string
  chunk_count: number
  created_at: string
  updated_at: string
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  /** 获取医学知识库的配置和就绪状态。 */
  return httpGet<KnowledgeStatus>('/knowledge/status')
}

export async function getKnowledgeDocuments(): Promise<{ items: KnowledgeDocument[]; page: number; page_size: number; total: number }> {
  /** 获取知识文档的入库状态列表。 */
  return httpGet('/knowledge/documents')
}
