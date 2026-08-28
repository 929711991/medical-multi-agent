from fastapi import Header, HTTPException, Request

from app.persistence.consumer_repositories import ConsumerUserRepository
from app.persistence.database import get_session_factory
from app.persistence.models import ConsumerUser
from app.services.consumer_auth import decode_consumer_token


async def get_current_consumer(authorization: str | None = Header(default=None)) -> ConsumerUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        payload = decode_consumer_token(authorization.split(" ", 1)[1].strip())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=401, detail="登录状态无效或已过期") from exc
    async with get_session_factory()() as session:
        user = await ConsumerUserRepository(session).get(payload["sub"])
        if user is None or user.status != "ACTIVE":
            raise HTTPException(status_code=401, detail="用户不存在或已停用")
        return user


def get_wechat_client(request: Request):
    return request.app.state.wechat_client


def get_consumer_job_queue(request: Request):
    return request.app.state.ai_job_queue


def get_rate_limiter(request: Request):
    return request.app.state.rate_limiter
