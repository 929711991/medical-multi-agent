import asyncio
import logging
import os
import socket

from app.core.logging import configure_logging
from app.graph.workflow import build_diagnosis_graph
from app.graph.consumer_workflow import build_consumer_consultation_graph
from app.persistence.checkpoint import mysql_checkpointer
from app.persistence.database import close_database, initialize_schema
from app.services.diagnosis_service import DiagnosisService
from app.services.job_queue import CONSUMER_JOB, DOCTOR_JOB, QueuedJob, RedisJobQueue

logger = logging.getLogger(__name__)


async def run_doctor_case_job(graph, payload: dict[str, str]) -> bool:
    """执行一个幂等 Doctor AI 病例任务。"""
    return await DiagnosisService.run_case(graph=graph, **payload)


async def run_consumer_analysis_job(graph, payload: dict[str, str]) -> bool:
    """延迟导入 Consumer 服务，保持 Doctor Worker 入口可独立启动。"""
    from app.services.consumer_consultation import ConsumerConsultationService

    return await ConsumerConsultationService.run_analysis_job(graph=graph, **payload)


async def process_job(queue: RedisJobQueue, doctor_graph, consumer_graph, job: QueuedJob) -> None:
    try:
        if job.job_type == DOCTOR_JOB:
            await run_doctor_case_job(doctor_graph, job.payload)
        elif job.job_type == CONSUMER_JOB:
            await run_consumer_analysis_job(consumer_graph, job.payload)
        else:
            raise ValueError("UNKNOWN_AI_JOB")
        await queue.acknowledge(job.message_id)
    except Exception as exc:
        error_code = getattr(exc, "error_code", None) or "AI_ANALYSIS_FAILED"
        logger.exception("AI Worker 任务失败", extra={"error_code": error_code})
        await queue.fail(job, error_code)


async def run_worker() -> None:
    configure_logging()
    await initialize_schema()
    queue = RedisJobQueue()
    consumer_name = f"{socket.gethostname()}-{os.getpid()}"
    try:
        async with mysql_checkpointer() as checkpointer:
            doctor_graph = build_diagnosis_graph(checkpointer=checkpointer)
            consumer_graph = build_consumer_consultation_graph(checkpointer=checkpointer)
            while True:
                await queue.heartbeat(consumer_name)
                job = await queue.read(consumer_name)
                if job is not None:
                    await process_job(queue, doctor_graph, consumer_graph, job)
    finally:
        await queue.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(run_worker())
