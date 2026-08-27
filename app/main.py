from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import cases, diagnosis, review
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.graph.workflow import build_diagnosis_graph
from app.mcp.client import get_mcp_manager, reset_mcp_manager
from app.persistence.checkpoint import mysql_checkpointer
from app.persistence.database import close_database, initialize_schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await initialize_schema()
    get_mcp_manager()
    async with mysql_checkpointer() as checkpointer:
        app.state.diagnosis_graph = build_diagnosis_graph(checkpointer=checkpointer)
        yield
    reset_mcp_manager()
    await close_database()


def create_app(*, graph: Any | None = None) -> FastAPI:
    selected_lifespan = None if graph is not None else lifespan
    app = FastAPI(
        title=get_settings().app_name,
        version="1.0.0",
        description="医疗辅助诊断系统；所有最终结论必须经过医生审核。",
        lifespan=selected_lifespan,
    )
    if graph is not None:
        app.state.diagnosis_graph = graph
    app.include_router(diagnosis.router, prefix=get_settings().api_prefix)
    app.include_router(cases.router, prefix=get_settings().api_prefix)
    app.include_router(review.router, prefix=get_settings().api_prefix)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": get_settings().app_name,
            "llm_configured": bool(get_settings().aliyun_llm_api_key),
            "rag_enabled": get_settings().rag_enabled,
        }

    @app.exception_handler(Exception)
    async def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": f"服务器内部错误：{type(exc).__name__}"})

    return app


app = create_app()
