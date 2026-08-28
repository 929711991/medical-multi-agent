import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.persistence.database import get_session_factory
from app.persistence.repositories import DoctorRepository
from app.schemas.auth import DoctorIdentity, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "medical_session"


def _sign(value: bytes) -> str:
    """为编码后的会话载荷生成 HMAC 签名。"""
    return hmac.new(get_settings().auth_secret.encode(), value, hashlib.sha256).hexdigest()


def _create_token(doctor_id: str) -> str:
    """为医生业务编号生成带签名和过期时间的会话令牌。"""
    payload = json.dumps(
        {"doctor_id": doctor_id, "exp": int(time.time()) + get_settings().auth_session_hours * 3600},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
    return f"{encoded.decode()}.{_sign(encoded)}"


def _read_token(token: str | None) -> str | None:
    """校验会话令牌，并在有效时返回医生业务编号。"""
    if not token or "." not in token:
        return None
    encoded_text, signature = token.rsplit(".", 1)
    encoded = encoded_text.encode()
    if not hmac.compare_digest(signature, _sign(encoded)):
        return None
    try:
        padded = encoded + b"=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) <= int(time.time()):
        return None
    doctor_id = payload.get("doctor_id")
    return doctor_id if isinstance(doctor_id, str) else None


async def get_current_doctor(
    request: Request,
    medical_session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> DoctorIdentity:
    """根据签名会话 Cookie 解析当前已登录医生。"""
    doctor_id = _read_token(medical_session)
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    session_store = getattr(request.app.state, "doctor_session_store", None)
    if session_store is not None:
        try:
            session_doctor_id = await session_store.get_user_id(medical_session or "")
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
        if session_doctor_id != doctor_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    async with get_session_factory()() as session:
        raw = await DoctorRepository(session).info(doctor_id)
    if not raw.get("found"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    return DoctorIdentity(
        doctor_id=raw["doctor_id"],
        name=raw["name"],
        department=raw["department"],
        title=raw.get("title"),
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest, response: Response) -> LoginResponse:
    """验证已落库的医生账号，并签发仅限 HTTP 访问的 Cookie。"""
    settings = get_settings()
    if not hmac.compare_digest(payload.password, settings.login_password):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    async with get_session_factory()() as session:
        if not hmac.compare_digest(payload.account, settings.login_account):
            raise HTTPException(status_code=401, detail="invalid login credentials")
        raw = await DoctorRepository(session).authenticate(payload.account, payload.password)
    if not raw.get("found"):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    user = DoctorIdentity(
        doctor_id=raw["doctor_id"],
        name=raw["name"],
        department=raw["department"],
        title=raw.get("title"),
    )
    token = _create_token(user.doctor_id)
    session_store = getattr(request.app.state, "doctor_session_store", None)
    if session_store is not None:
        try:
            # 医生登录成功后才写入 Redis，会话 TTL 与 Cookie 保持一致。
            await session_store.save(token, user.doctor_id, settings.auth_session_hours * 3600)
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=get_settings().auth_cookie_secure,
        samesite="lax",
        max_age=get_settings().auth_session_hours * 3600,
        path="/",
    )
    return LoginResponse(user=user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    medical_session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> None:
    """删除 Redis 会话并清除浏览器中的身份认证 Cookie。"""
    session_store = getattr(request.app.state, "doctor_session_store", None)
    if session_store is not None and medical_session:
        try:
            await session_store.revoke(medical_session)
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="登录服务暂不可用，请稍后重试") from exc
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


@router.get("/me", response_model=DoctorIdentity)
async def me(doctor: DoctorIdentity = Depends(get_current_doctor)) -> DoctorIdentity:
    """返回当前已登录医生的对外身份信息。"""
    return doctor
