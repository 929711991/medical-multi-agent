from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeDocumentResponse(BaseModel):
    id: str
    title: str
    source: str
    source_type: str
    version: str | None = None
    published_at: datetime | None = None
    checksum: str
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeStatusResponse(BaseModel):
    rag_enabled: bool
    rag_required: bool
    rag_ready: bool
    milvus: str
    collection: str
    embedding_model: str | None
    knowledge_documents: int = 0
    message: str | None = None


class KnowledgeDocumentPage(BaseModel):
    items: list[KnowledgeDocumentResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
