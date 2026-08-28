from app.core.config import get_settings


def chunk_text(text: str) -> list[str]:
    settings = get_settings()
    normalized = "\n".join(line.strip() for line in text.replace("\r\n", "\n").split("\n"))
    normalized = normalized.strip()
    if not normalized:
        return []

    size = settings.rag_chunk_size
    overlap = settings.rag_chunk_overlap
    if overlap >= size:
        raise ValueError("RAG_CHUNK_OVERLAP 必须小于 RAG_CHUNK_SIZE")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            candidates = [normalized.rfind(marker, start, end) for marker in ("\n\n", "。", "；", "\n")]
            boundary = max(candidates)
            if boundary > start + size // 2:
                end = boundary + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks
