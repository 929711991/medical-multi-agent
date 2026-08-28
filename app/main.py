from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import auth, cases, dashboard, diagnosis, knowledge, patients, review
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.graph.workflow import build_diagnosis_graph
from app.mcp.client import get_mcp_manager, reset_mcp_manager
from app.persistence.checkpoint import mysql_checkpointer
from app.persistence.database import close_database, initialize_schema
from app.services.health import collect_health


logger = logging.getLogger(__name__)


class UTF8JSONResponse(JSONResponse):
    """显式声明 UTF-8，避免 Windows PowerShell 错误解码中文 JSON。"""

    media_type = "application/json; charset=utf-8"


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
        default_response_class=UTF8JSONResponse,
    )
    if graph is not None:
        app.state.diagnosis_graph = graph
    app.include_router(diagnosis.router, prefix=get_settings().api_prefix)
    app.include_router(cases.router, prefix=get_settings().api_prefix)
    app.include_router(review.router, prefix=get_settings().api_prefix)
    app.include_router(auth.router, prefix=get_settings().api_prefix)
    app.include_router(patients.router, prefix=get_settings().api_prefix)
    app.include_router(dashboard.router, prefix=get_settings().api_prefix)
    app.include_router(knowledge.router, prefix=get_settings().api_prefix)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        if graph is not None:
            return {
                "status": "ok",
                "service": "医疗辅助多智能体 V1",
                "llm_configured": bool(get_settings().aliyun_llm_api_key),
                "rag_enabled": get_settings().rag_enabled,
            }
        return await collect_health()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        summaries: list[str] = []
        for item in errors:
            location = ".".join(str(part) for part in item.get("loc", []))
            message = str(item.get("msg", "参数校验失败")).removeprefix("Value error, ")
            summaries.append(f"{location}: {message}")
        logger.warning(
            "request_validation_failed method=%s path=%s errors=%s",
            request.method,
            request.url.path,
            " | ".join(summaries),
        )
        friendly = summaries[0].split(": ", 1)[-1] if summaries else "提交的信息不符合要求，请检查后重试"
        return UTF8JSONResponse(status_code=422, content={"detail": friendly})

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error method=%s path=%s", request.method, request.url.path)
        return UTF8JSONResponse(status_code=500, content={"detail": "服务器处理请求时出现异常，请稍后重试"})

    return app


app = create_app()
