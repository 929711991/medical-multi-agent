from typing import Any

from app.core.config import get_settings


def patient_server_connection() -> dict[str, Any]:
    """生成患者 MCP 服务的连接配置。"""
    return {
        "url": get_settings().mcp_server_url,
        "transport": "streamable_http",
        "timeout": get_settings().mcp_connect_timeout_seconds,
    }
