from langchain_core.tools import BaseTool

from app.mcp.client import get_mcp_manager


async def get_patient_tools() -> list[BaseTool]:
    """创建患者查询与更新使用的受控 MCP 工具集合。"""
    return await get_mcp_manager().get_tools()
