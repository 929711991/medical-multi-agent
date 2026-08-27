from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeEvidence(BaseModel):
    source_type: str = "rag"
    document_id: str
    chunk_id: str
    title: str
    excerpt: str
    retrieved_at: datetime
    score: float | None = Field(default=None, ge=0, le=1)


class KnowledgeSearchResult(BaseModel):
    enabled: bool
    evidence: list[KnowledgeEvidence] = Field(default_factory=list)
    message: str

