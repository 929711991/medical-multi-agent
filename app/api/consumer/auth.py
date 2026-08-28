import hashlib
import hmac

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from redis.exceptions import RedisError

from app.api.consumer.dependencies import get_current_consumer, get_wechat_client
from app.core.config import get_settings
from app.persistence.consumer_repositories import ConsumerUserRepository
from app.persistence.database import get_session_factory
from app.persistence.models import ConsumerUser
from app.schemas.consumer import (
    ConsumerIdentity,
    ConsumerLoginResponse,
    H5LoginRequest,
    WeChatLoginRequest,
)
from app.services.consumer_auth import issue_consumer_token

router = APIRouter(prefix="/auth", tags=["consumer-auth"])


def _identity(user: ConsumerUser) -> ConsumerIdentity:
    return ConsumerIdentity(user_id=str(user.id), nickname=user.nickname, avatar=user.avatar)


async def _login_response(request: Request, user: ConsumerUser) -> ConsumerLoginResponse:
    token, expires_in = issue_consumer_token(str(user.id))
    session_store = getattr(request.app.state, "consumer_session_store", None)
    if session_store is not None:
        # 只有登录成功并完成签发后，才把会话摘要写入 Redis。
        await session_store.save(token, str(user.id), expires_in)
    return ConsumerLoginResponse(
        access_token=token, expires_in=expires_in, user=_identity(user)
    )


@router.post("/wechat", response_model=ConsumerLoginResponse)
async def wechat_login(
    request: Request, payload: WeChatLoginRequest, client=Depends(get_wechat_client)
):
    try:
        wx_session = await client.exchange_code(payload.code)
        async with get_session_factory()() as session:
            user = await ConsumerUserRepository(session).create_or_update(
                openid=wx_session.openid,
                unionid=wx_session.unionid,
                nickname=payload.nickname,
                avatar=payload.avatar,
            )
        return await _login_response(request, user)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="微信登录服务暂不可用，请稍后重试") from exc
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="微信登录服务尚未配置") from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="微信登录凭证无效，请重新登录") from exc


@router.post("/h5", response_model=ConsumerLoginResponse)
async def h5_login(request: Request, payload: H5LoginRequest):
    """使用明确配置的 H5 验收账号登录，并由后端签发 Consumer token。"""
    settings = get_settings()
    try:
        settings.validate_h5_consumer_login()
        account = settings.h5_consumer_account
        password = settings.h5_consumer_password
        assert account is not None and password is not None
        if not hmac.compare_digest(payload.account, account) or not hmac.compare_digest(
            payload.password, password
        ):
            raise ValueError("H5_CREDENTIALS_INVALID")

        # 身份标识由服务端派生，客户端不能通过请求体伪造 openid。
        openid = "h5-acceptance-" + hashlib.sha256(account.encode("utf-8")).hexdigest()
        async with get_session_factory()() as session:
            user = await ConsumerUserRepository(session).create_or_update(
                openid=openid,
                unionid=None,
                nickname="小狐狸健康助手用户",
                avatar=None,
            )
        return await _login_response(request, user)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="H5 验收登录尚未配置") from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="H5 登录账号或密码错误") from exc


@router.post("/logout", status_code=204)
async def consumer_logout(
    request: Request,
    authorization: str | None = Header(default=None),
    _: ConsumerUser = Depends(get_current_consumer),
) -> None:
    """注销当前 Consumer 会话，使 Redis 中的 token 立即失效。"""
    session_store = getattr(request.app.state, "consumer_session_store", None)
    if session_store is not None and authorization:
        token = authorization.split(" ", 1)[1].strip()
        try:
            await session_store.revoke(token)
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
