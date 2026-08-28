import json
from dataclasses import dataclass
from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import get_settings


DOCTOR_JOB = "run_doctor_case_job"
CONSUMER_JOB = "run_consumer_analysis_job"


class AIJobQueue(Protocol):
    async def enqueue_doctor_case(self, **payload: str) -> str: ...

    async def enqueue_consumer_analysis(self, **payload: str) -> str: ...


@dataclass(frozen=True)
class QueuedJob:
    message_id: str
    job_type: str
    payload: dict[str, Any]


class RedisJobQueue:
    """基于 Redis Streams 的持久 AI 队列，提供消费确认、去重和失败队列。"""

    stream = "job:medical:stream"
    dead_letter_stream = "job:medical:dead-letter"
    group = "medical-ai-workers"

    def __init__(self, redis: Redis | None = None):
        self.redis = redis or Redis.from_url(get_settings().redis_url, decode_responses=True)
        self._owns_client = redis is None

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _enqueue(self, job_type: str, dedupe_id: str, payload: dict[str, Any]) -> str:
        dedupe_key = f"job:dedupe:{job_type}:{dedupe_id}"
        claimed = await self.redis.set(dedupe_key, "1", nx=True)
        if not claimed:
            return "duplicate"
        try:
            return str(
                await self.redis.xadd(
                    self.stream,
                    {"job_type": job_type, "payload": json.dumps(payload, ensure_ascii=False)},
                )
            )
        except Exception:
            await self.redis.delete(dedupe_key)
            raise

    async def enqueue_doctor_case(self, **payload: str) -> str:
        return await self._enqueue(DOCTOR_JOB, payload["case_id"], payload)

    async def enqueue_consumer_analysis(self, **payload: str) -> str:
        return await self._enqueue(
            CONSUMER_JOB, payload.get("job_id", payload["consultation_id"]), payload
        )

    async def read(self, consumer_name: str, *, block_ms: int = 5000) -> QueuedJob | None:
        await self.ensure_group()
        rows = await self.redis.xreadgroup(
            self.group,
            consumer_name,
            {self.stream: ">"},
            count=1,
            block=block_ms,
        )
        if not rows:
            return None
        _, messages = rows[0]
        message_id, fields = messages[0]
        return QueuedJob(
            message_id=str(message_id),
            job_type=str(fields["job_type"]),
            payload=json.loads(fields["payload"]),
        )

    async def acknowledge(self, message_id: str) -> None:
        await self.redis.xack(self.stream, self.group, message_id)

    async def fail(self, job: QueuedJob, error_code: str) -> None:
        await self.redis.xadd(
            self.dead_letter_stream,
            {
                "source_id": job.message_id,
                "job_type": job.job_type,
                "payload": json.dumps(job.payload, ensure_ascii=False),
                "error_code": error_code,
            },
        )
        await self.acknowledge(job.message_id)

    async def heartbeat(self, worker_name: str) -> None:
        await self.redis.set(f"job:worker:heartbeat:{worker_name}", "ready", ex=30)

    async def worker_ready(self) -> bool:
        keys = await self.redis.keys("job:worker:heartbeat:*")
        return bool(keys)

    async def close(self) -> None:
        if self._owns_client:
            await self.redis.aclose()


class InlineDiagnosisQueue:
    """仅用于显式注入诊断图的隔离测试应用，不启动进程后台任务。"""

    def __init__(self, graph: Any):
        self.graph = graph

    async def enqueue_doctor_case(self, **payload: str) -> str:
        from app.services.diagnosis_service import DiagnosisService

        await DiagnosisService.run_case(graph=self.graph, **payload)
        return "inline"

    async def enqueue_consumer_analysis(self, **payload: str) -> str:
        raise NotImplementedError("隔离 Doctor 图不处理 Consumer 任务")
