import { request } from '../utils/request'

export const ragEnabled = import.meta.env.VITE_FEATURE_RAG !== 'false'

export interface KnowledgeStatus {
  rag_enabled: boolean
  rag_required: boolean
  rag_ready: boolean
  milvus: string
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
  return (await request.get<KnowledgeStatus>('/knowledge/status')).data
}

export async function getKnowledgeDocuments(): Promise<{ items: KnowledgeDocument[]; page: number; page_size: number; total: number }> {
  return (await request.get('/knowledge/documents')).data
}
