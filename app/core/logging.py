import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact_pii(value: str) -> str:
    """在写入应用日志前遮盖常见的直接身份标识。"""
    value = PHONE_RE.sub("[REDACTED_PHONE]", value)
    return EMAIL_RE.sub("[REDACTED_EMAIL]", value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """将日志记录序列化为已脱敏的 JSON 对象。"""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_pii(record.getMessage()),
        }
        for key in ("case_id", "thread_id", "graph_node", "tool_name", "duration_ms", "status"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = redact_pii(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """按照配置日志级别安装结构化 JSON 处理器。"""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(get_settings().log_level.upper())
