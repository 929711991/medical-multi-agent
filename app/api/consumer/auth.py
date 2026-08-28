from fastapi import APIRouter, Depends, HTTPException

from app.api.consumer.dependencies import get_current_consumer, get_wechat_client
from app.persistence.consumer_repositories import ConsumerUserRepository
from app.persistence.database import get_session_factory
from app.persistence.models import ConsumerUser
from app.schemas.consumer import (
    ConsumerIdentity,
    ConsumerLoginResponse,
    WeChatLoginRequest,
)
from app.services.consumer_auth import issue_consumer_token

router = APIRouter(prefix="/auth", tags=["consumer-auth"])


def _identity(user: ConsumerUser) -> ConsumerIdentity:
    return ConsumerIdentity(user_id=str(user.id), nickname=user.nickname, avatar=user.avatar)


@router.post("/wechat", response_model=ConsumerLoginResponse)
async def wechat_login(payload: WeChatLoginRequest, client=Depends(get_wechat_client)):
    try:
        wx_session = await client.exchange_code(payload.code)
        async with get_session_factory()() as session:
            user = await ConsumerUserRepository(session).create_or_update(
                openid=wx_session.openid,
                unionid=wx_session.unionid,
                nickname=payload.nickname,
                avatar=payload.avatar,
            )
        token, expires_in = issue_consumer_token(str(user.id))
        return ConsumerLoginResponse(
            access_token=token, expires_in=expires_in, user=_identity(user)
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="微信登录服务尚未配置") from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="微信登录凭证无效，请重新登录") from exc

