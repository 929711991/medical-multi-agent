from langchain_core.tools import BaseTool

from app.mcp.client import get_mcp_manager


async def get_doctor_tool() -> BaseTool:
    """创建返回当前医生身份信息的 MCP 工具。"""
    tools = await get_mcp_manager().tool_map()
    return tools["get_doctor_info"]
