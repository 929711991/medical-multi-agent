import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class WeChatSession:
    openid: str
    unionid: str | None = None


class WeChatClient:
    endpoint = "https://api.weixin.qq.com/sns/jscode2session"

    async def exchange_code(self, code: str) -> WeChatSession:
        settings = get_settings()
        settings.validate_wechat()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                self.endpoint,
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
        response.raise_for_status()
        payload = response.json()
        openid = payload.get("openid")
        session_key = payload.get("session_key")
        if (
            payload.get("errcode")
            or not isinstance(openid, str)
            or not openid.strip()
            or not isinstance(session_key, str)
            or not session_key.strip()
        ):
            raise ValueError("WECHAT_CODE_INVALID")
        unionid = payload.get("unionid")
        return WeChatSession(
            openid=openid,
            unionid=unionid if isinstance(unionid, str) else None,
        )


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_consumer_token(user_id: str) -> tuple[str, int]:
    settings = get_settings()
    settings.validate_consumer_auth()
    expires_in = settings.consumer_token_hours * 3600
    body = _b64encode(
        json.dumps(
            {"sub": user_id, "typ": "consumer", "exp": int(time.time()) + expires_in},
            separators=(",", ":"),
        ).encode()
    )
    secret = settings.consumer_auth_secret
    assert secret is not None
    signature = _b64encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}", expires_in


def decode_consumer_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    settings.validate_consumer_auth()
    try:
        body, signature = token.split(".", 1)
        secret = settings.consumer_auth_secret
        assert secret is not None
        expected = _b64encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(_b64decode(body))
        subject = payload.get("sub")
        if (
            payload.get("typ") != "consumer"
            or not isinstance(subject, str)
            or not subject.strip()
            or int(payload.get("exp", 0)) <= int(time.time())
        ):
            raise ValueError
        return payload
    except Exception as exc:
        raise ValueError("CONSUMER_TOKEN_INVALID") from exc
