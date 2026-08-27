from typing import Any

from app.core.config import get_settings


def patient_server_connection() -> dict[str, Any]:
    return {
        "url": get_settings().mcp_server_url,
        "transport": "streamable_http",
        "timeout": get_settings().mcp_connect_timeout_seconds,
    }

