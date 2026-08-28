import hashlib

from redis.asyncio import Redis


class RedisSessionStore:
    """将登录 token 的会话摘要保存到 Redis，支持过期和服务端失效。"""

    def __init__(self, redis: Redis, key_prefix: str):
        self.redis = redis
        self.key_prefix = key_prefix

    def _key(self, token: str) -> str:
        # Redis 只保存 token 摘要，不保存可直接使用的 bearer token。
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}{digest}"

    async def save(self, token: str, user_id: str, expires_in: int) -> None:
        await self.redis.set(self._key(token), user_id, ex=expires_in)

    async def get_user_id(self, token: str) -> str | None:
        value = await self.redis.get(self._key(token))
        if value is None:
            return None
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    async def revoke(self, token: str) -> None:
        await self.redis.delete(self._key(token))


class ConsumerSessionStore(RedisSessionStore):
    """Consumer 用户专用 Redis 会话空间。"""

    def __init__(self, redis: Redis):
        super().__init__(redis, "consumer:session:")


class DoctorSessionStore(RedisSessionStore):
    """Web 医生专用 Redis 会话空间。"""

    def __init__(self, redis: Redis):
        super().__init__(redis, "doctor:session:")
