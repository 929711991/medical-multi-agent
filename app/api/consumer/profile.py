from fastapi import APIRouter, Depends

from app.api.consumer.auth import _identity
from app.api.consumer.dependencies import get_current_consumer
from app.persistence.models import ConsumerUser
from app.schemas.consumer import ConsumerIdentity

router = APIRouter(tags=["consumer-profile"])


@router.get("/me", response_model=ConsumerIdentity)
async def me(user: ConsumerUser = Depends(get_current_consumer)) -> ConsumerIdentity:
    return _identity(user)
