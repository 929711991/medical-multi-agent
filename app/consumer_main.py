from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.consumer import auth, consultations, patients, profile, sharing
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.persistence.database import close_database, initialize_schema
from app.services.consumer_auth import WeChatClient
from app.services.health import collect_health
from app.services.job_queue import RedisJobQueue
from app.services.rate_limit import RateLimitExceeded, RedisRateLimiter
from app.services.consumer_sessions import ConsumerSessionStore


class ConsumerJSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await initialize_schema()
    queue = RedisJobQueue()
    app.state.ai_job_queue = queue
    app.state.rate_limiter = RedisRateLimiter(queue.redis)
    app.state.consumer_session_store = ConsumerSessionStore(queue.redis)
    app.state.wechat_client = WeChatClient()
    try:
        yield
    finally:
        await queue.close()
        await close_database()


def create_consumer_app(
    *, queue: Any | None = None, wechat_client: Any | None = None, rate_limiter: Any | None = None
) -> FastAPI:
    injected = queue is not None or wechat_client is not None or rate_limiter is not None
    app = FastAPI(
        title="Medical Multi-Agent Consumer API",
        version="1.2.0",
        description="AI 健康助手；AI 生成内容不替代医生诊疗。",
        lifespan=None if injected else lifespan,
        default_response_class=ConsumerJSONResponse,
    )
    if queue is not None:
        app.state.ai_job_queue = queue
        if hasattr(queue, "redis"):
            app.state.consumer_session_store = ConsumerSessionStore(queue.redis)
    if wechat_client is not None:
        app.state.wechat_client = wechat_client
    if rate_limiter is not None:
        app.state.rate_limiter = rate_limiter
    prefix = f"{get_settings().api_prefix}/consumer"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(profile.router, prefix=prefix)
    app.include_router(patients.router, prefix=prefix)
    app.include_router(consultations.router, prefix=prefix)
    app.include_router(sharing.router, prefix=prefix)

    @app.middleware("http")
    async def ip_rate_limit(request: Request, call_next):
        limiter = getattr(request.app.state, "rate_limiter", None)
        if limiter is not None and request.url.path.startswith(prefix):
            ip = request.client.host if request.client else "unknown"
            try:
                await limiter.check(
                    "ip", ip, get_settings().rate_limit_ip_per_minute, 60
                )
            except RateLimitExceeded:
                return ConsumerJSONResponse(
                    status_code=429,
                    content={"error_code": "RATE_LIMITED", "detail": "请求过于频繁，请稍后再试"},
                )
            except Exception:
                return ConsumerJSONResponse(
                    status_code=503,
                    content={"error_code": "REDIS_UNAVAILABLE", "detail": "服务暂不可用"},
                )
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        if injected:
            return {
                "status": "ok",
                "service": "Medical Multi-Agent Consumer API",
                "wechat_configured": bool(
                    get_settings().wechat_app_id and get_settings().wechat_app_secret
                ),
            }
        return await collect_health()

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        detail = str(first.get("msg", "提交的信息不符合要求")).removeprefix("Value error, ")
        return ConsumerJSONResponse(status_code=422, content={"error_code": "VALIDATION_ERROR", "detail": detail})

    return app


app = create_consumer_app()
