import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.api.consumer.dependencies import get_current_consumer
from app.persistence.consumer_repositories import ConsultationRepository, ShareGrantRepository
from app.persistence.database import get_session_factory
from app.persistence.models import ConsumerUser
from app.schemas.consumer import ShareCreateRequest, ShareCreateResponse

router = APIRouter(tags=["consumer-sharing"])


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/consultations/{consultation_id}/share", response_model=ShareCreateResponse)
async def create_share(
    consultation_id: str,
    payload: ShareCreateRequest,
    user: ConsumerUser = Depends(get_current_consumer),
) -> ShareCreateResponse:
    async with get_session_factory()() as session:
        consultation = await ConsultationRepository(session).get(consultation_id)
        if consultation is None or consultation.consumer_user_id != user.id:
            raise HTTPException(status_code=403, detail="只有咨询创建者可以分享")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        grant = await ShareGrantRepository(session).create(
            consultation_id=consultation_id,
            created_by=user.id,
            token_hash=_hash(token),
            permission=payload.permission,
            expires_at=expires_at,
            max_uses=payload.max_uses,
        )
        return ShareCreateResponse(grant_id=str(grant.id), share_token=token, expires_at=expires_at)


@router.post("/shares/{token}/redeem")
async def redeem_share(
    token: str, user: ConsumerUser = Depends(get_current_consumer)
) -> dict:
    async with get_session_factory()() as session:
        try:
            grant = await ShareGrantRepository(session).redeem(_hash(token), user.id)
        except LookupError as exc:
            messages = {
                "SHARE_TOKEN_EXPIRED": "分享链接已过期",
                "SHARE_TOKEN_MAX_USES": "分享链接使用次数已达上限",
            }
            raise HTTPException(status_code=410, detail=messages.get(str(exc), "分享链接无效")) from exc
        return {"consultation_id": str(grant.consultation_id), "permission": grant.permission}


@router.delete("/shares/{grant_id}", status_code=204)
async def revoke_share(
    grant_id: str, user: ConsumerUser = Depends(get_current_consumer)
) -> None:
    async with get_session_factory()() as session:
        if not await ShareGrantRepository(session).revoke(grant_id, user.id):
            raise HTTPException(status_code=404, detail="未找到可撤销的分享授权")
