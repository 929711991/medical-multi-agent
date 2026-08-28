import asyncio
import hashlib
from pathlib import Path

from app.core.config import get_settings
from app.persistence.database import get_session_factory, initialize_schema
from app.persistence.repositories import KnowledgeRepository
from app.rag.chunker import chunk_text
from app.rag.document_loader import load_document, supported_document
from app.rag.embedding import embed_documents
from app.rag.redis_store import delete_document, ensure_index, upsert

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "knowledge" / "source"


def _document_id(path: Path) -> str:
    """根据知识文档相对路径生成稳定的文档业务编号。"""
    relative = path.relative_to(SOURCE_ROOT).as_posix()
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()[:32]


def _checksum(text: str) -> str:
    """计算文档正文校验和，用于判断是否需要重复入库。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ingest_file(path: Path) -> str:
    """读取、分片、向量化并持久化单个医学知识文档。"""
    settings = get_settings()
    settings.validate_rag()
    text = load_document(path).strip()
    if not text:
        raise ValueError(f"知识文档为空：{path}")

    document_id = _document_id(path)
    checksum = _checksum(text)
    source = path.relative_to(SOURCE_ROOT).as_posix()
    source_type = path.suffix.lower().lstrip(".")

    async with get_session_factory()() as session:
        repository = KnowledgeRepository(session)
        existing = await repository.get(document_id)
        # 内容未变化时保留现有向量，避免重复调用嵌入服务并降低索引抖动。
        if existing and existing.status == "READY" and existing.checksum == checksum:
            return f"SKIP {source}"
        await repository.save_state(
            document_id=document_id,
            title=path.stem,
            source=source,
            source_type=source_type,
            version=None,
            checksum=checksum,
            status="PENDING",
            chunk_count=0,
        )

    chunks = chunk_text(text)
    vectors = await embed_documents(chunks)
    if not vectors or len(vectors) != len(chunks):
        raise RuntimeError(f"Embedding 返回数量异常：{source}")

    await ensure_index(len(vectors[0]))
    # 先删除同一文档的旧分片，再批量写入新分片，保证检索结果不会混入旧版本。
    await delete_document(document_id)
    rows = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        chunk_id = f"{document_id}-{index:05d}"
        rows.append(
            {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "title": path.stem[:512],
                "text": chunk,
                "source": source[:2048],
                "source_type": source_type[:64],
                "version": "",
                "embedding": vector,
            }
        )
    await upsert(rows)

    async with get_session_factory()() as session:
        await KnowledgeRepository(session).save_state(
            document_id=document_id,
            title=path.stem,
            source=source,
            source_type=source_type,
            version=None,
            checksum=checksum,
            status="READY",
            chunk_count=len(rows),
        )
    return f"READY {source} chunks={len(rows)}"


async def main() -> None:
    """扫描知识目录并逐个执行入库，记录失败文档后统一返回失败状态。"""
    await initialize_schema()
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in SOURCE_ROOT.rglob("*") if supported_document(path))
    if not files:
        raise RuntimeError(f"没有可入库医学知识文档：{SOURCE_ROOT}")

    failures: list[str] = []
    for path in files:
        try:
            print(await ingest_file(path))
        except Exception as exc:
            # 单个文档失败不影响其余文档继续处理，最后统一抛出失败汇总。
            failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
            async with get_session_factory()() as session:
                await KnowledgeRepository(session).save_state(
                    document_id=_document_id(path),
                    title=path.stem,
                    source=path.relative_to(SOURCE_ROOT).as_posix(),
                    source_type=path.suffix.lower().lstrip("."),
                    version=None,
                    checksum=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "",
                    status="FAILED",
                    chunk_count=0,
                )
    if failures:
        raise RuntimeError("RAG 入库失败：" + " | ".join(failures))


if __name__ == "__main__":
    asyncio.run(main())
