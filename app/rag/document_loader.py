from pathlib import Path


def load_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("读取 PDF 医学知识文档需要安装 pypdf") from exc
        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    raise ValueError(f"暂不支持的知识文档格式：{suffix}")


def supported_document(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf"}
