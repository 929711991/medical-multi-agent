from langchain_core.tools import BaseTool

from app.mcp.client import get_mcp_manager


async def get_patient_tools() -> list[BaseTool]:
    return await get_mcp_manager().get_tools()

