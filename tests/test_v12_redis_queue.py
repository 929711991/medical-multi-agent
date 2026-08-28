from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.core.config import get_settings
from app.services.job_queue import RedisJobQueue
from app.services.rate_limit import RateLimitExceeded, RedisRateLimiter


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_redis_queue_dedupe_and_rate_limit() -> None:
    suffix = uuid4().hex
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    queue = RedisJobQueue(redis)
    queue.stream = f"job:test:{suffix}:stream"
    queue.dead_letter_stream = f"job:test:{suffix}:dead"
    queue.group = f"test-workers-{suffix}"
    case_id = f"case-{suffix}"
    dedupe_key = f"job:dedupe:run_doctor_case_job:{case_id}"
    rate_key = f"rate_limit:test:{suffix}"
    try:
        assert await redis.ping()
        indexes = await redis.execute_command("FT._LIST")
        assert isinstance(indexes, list)
        message_id = await queue.enqueue_doctor_case(
            case_id=case_id,
            thread_id=case_id,
            patient_id="patient-test",
            question="queue integration",
        )
        assert message_id != "duplicate"
        assert (
            await queue.enqueue_doctor_case(
                case_id=case_id,
                thread_id=case_id,
                patient_id="patient-test",
                question="queue integration duplicate",
            )
        ) == "duplicate"
        job = await queue.read(f"consumer-{suffix}", block_ms=100)
        assert job is not None
        assert job.payload["case_id"] == case_id
        await queue.acknowledge(job.message_id)
        pending = await redis.xpending(queue.stream, queue.group)
        assert pending["pending"] == 0

        limiter = RedisRateLimiter(redis)
        assert await limiter.check("test", suffix, 2, 60) == 1
        assert await limiter.check("test", suffix, 2, 60) == 2
        with pytest.raises(RateLimitExceeded):
            await limiter.check("test", suffix, 2, 60)
        ttl = await redis.ttl(rate_key)
        assert 0 < ttl <= 60
    finally:
        await redis.delete(queue.stream, queue.dead_letter_stream, dedupe_key, rate_key)
        await redis.aclose()
