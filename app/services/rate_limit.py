from redis.asyncio import Redis

from app.core.config import get_settings


class RateLimitExceeded(Exception):
    error_code = "RATE_LIMITED"


class RedisRateLimiter:
    """使用带 TTL 的 Redis 计数器实施固定窗口限流，和 RAG key 空间隔离。"""

    def __init__(self, redis: Redis | None = None):
        self.redis = redis or Redis.from_url(get_settings().redis_url, decode_responses=True)
        self._owns_client = redis is None

    async def check(self, scope: str, identity: str, limit: int, window_seconds: int) -> int:
        key = f"rate_limit:{scope}:{identity}"
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, window_seconds, nx=True)
            count, _ = await pipeline.execute()
        if int(count) > limit:
            raise RateLimitExceeded
        return int(count)

    async def close(self) -> None:
        if self._owns_client:
            await self.redis.aclose()
