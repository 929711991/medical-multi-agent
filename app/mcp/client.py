import asyncio
import json
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.mcp.config import patient_server_connection


class MCPClientManager:
    def __init__(self) -> None:
        """初始化延迟加载的 MCP 客户端状态。"""
        self.client = MultiServerMCPClient({"patient": patient_server_connection()})
        self._tools: list[BaseTool] | None = None
        self._lock = asyncio.Lock()

    async def get_tools(self) -> list[BaseTool]:
        """连接患者 MCP 服务并缓存允许调用的工具。"""
        if self._tools is None:
            async with self._lock:
                if self._tools is None:
                    self._tools = await asyncio.wait_for(
                        self.client.get_tools(server_name="patient"),
                        timeout=15,
                    )
        return self._tools

    async def tool_map(self) -> dict[str, BaseTool]:
        """按照工具名称返回 MCP 工具映射。"""
        return {tool.name: tool for tool in await self.get_tools()}

    async def invoke_structured(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """调用 MCP 工具，并把适配器返回的文本内容还原为结构化字典。"""
        tools = await self.tool_map()
        if tool_name not in tools:
            raise LookupError(f"未找到 MCP 工具：{tool_name}")
        result = await tools[tool_name].ainvoke(arguments)
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            for block in result:
                if isinstance(block, dict) and block.get("type") == "text":
                    parsed = json.loads(block["text"])
                    if isinstance(parsed, dict):
                        return parsed
        raise TypeError(f"MCP 工具 {tool_name} 未返回结构化对象内容")


_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    """返回进程内复用的 MCP 客户端管理器。"""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager


def reset_mcp_manager() -> None:
    """清除 MCP 管理器缓存，供测试和配置刷新使用。"""
    global _manager
    _manager = None
