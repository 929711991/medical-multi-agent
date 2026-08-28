import asyncio
import atexit
import hashlib
import json
import time
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.persistence.consumer_repositories import ConsumerUserRepository
from app.persistence.database import close_database, get_session_factory
from app.persistence.repositories import KnowledgeRepository
from app.rag.embedding import embed_documents
from app.rag.redis_store import delete_document, ensure_index, reset_redis_client, upsert
from app.services.consumer_auth import issue_consumer_token


async def _create_acceptance_user(suffix: str) -> str:
    async with get_session_factory()() as session:
        user = await ConsumerUserRepository(session).create_or_update(
            openid=f"acceptance-openid-{suffix}",
            unionid=None,
            nickname="V12验收用户",
            avatar=None,
        )
        user_id = str(user.id)
    await close_database()
    return user_id


async def _install_acceptance_knowledge(suffix: str) -> str:
    reset_redis_client()
    document_id = f"consumer-acceptance-{suffix}"
    text = (
        "V1.2 跨端验收知识：右下腹进行性疼痛伴恶心需要及时线下评估；"
        "持续压榨性胸痛伴大汗或呼吸困难属于急症警示，应立即呼叫急救。"
    )
    vector = (await embed_documents([text]))[0]
    await ensure_index(len(vector))
    await upsert(
        [
            {
                "id": f"{document_id}-00000",
                "document_id": document_id,
                "chunk_id": f"{document_id}-00000",
                "title": "V1.2 Consumer 跨端 RAG 验收知识",
                "text": text,
                "source": "acceptance-consumer-e2e",
                "source_type": "test",
                "version": "1.2",
                "embedding": vector,
            }
        ]
    )
    async with get_session_factory()() as session:
        await KnowledgeRepository(session).save_state(
            document_id=document_id,
            title="V1.2 Consumer 跨端 RAG 验收知识",
            source="acceptance-consumer-e2e",
            source_type="test",
            version="1.2",
            checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            status="READY",
            chunk_count=1,
        )
    await close_database()
    return document_id


async def _remove_acceptance_knowledge(document_id: str) -> None:
    reset_redis_client()
    await delete_document(document_id)
    async with get_session_factory()() as session:
        document = await KnowledgeRepository(session).get(document_id)
        if document is not None:
            await session.delete(document)
            await session.commit()
    await close_database()
    reset_redis_client()


def _wait_consultation(client: httpx.Client, consultation_id: str, terminal: set[str]) -> dict:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        response = client.get(f"/consultations/{consultation_id}")
        response.raise_for_status()
        value = response.json()
        if value["status"] in terminal:
            return value
        time.sleep(1)
    raise TimeoutError(f"consultation {consultation_id} did not reach {terminal}")


def _wait_case(client: httpx.Client, case_id: str) -> dict:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/cases/{case_id}")
        response.raise_for_status()
        value = response.json()
        if value["status"] in {"WAITING_REVIEW", "FAILED"}:
            return value
        time.sleep(1)
    raise TimeoutError(f"case {case_id} did not finish AI analysis")


def main() -> None:
    suffix = uuid4().hex[:10]
    acceptance_document_id = asyncio.run(_install_acceptance_knowledge(suffix))
    atexit.register(lambda: asyncio.run(_remove_acceptance_knowledge(acceptance_document_id)))
    user_id = asyncio.run(_create_acceptance_user(suffix))
    token, _ = issue_consumer_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(
        base_url="http://127.0.0.1:8002/api/v1/consumer",
        headers=headers,
        timeout=30,
    ) as consumer:
        patient_response = consumer.post(
            "/patients",
            json={
                "name": f"V12跨端验收-{suffix}",
                "sex": "female",
                "relation_type": "self",
                "self_reported_history": ["自述有高血压史"],
            },
        )
        patient_response.raise_for_status()
        patient_id = patient_response.json()["patient_id"]

        gastro = consumer.post("/consultations", json={"patient_id": patient_id})
        gastro.raise_for_status()
        gastro_id = gastro.json()["id"]
        first = consumer.post(
            f"/consultations/{gastro_id}/messages",
            json={"client_message_id": f"g1-{suffix}", "content": "右下腹越来越疼"},
        )
        first.raise_for_status()
        second = consumer.post(
            f"/consultations/{gastro_id}/messages",
            json={
                "client_message_id": f"g2-{suffix}",
                "content": "已经持续两天，疼痛8分，伴有恶心",
            },
        )
        second.raise_for_status()
        assert second.json()["intake"]["ready_for_analysis"] is True
        analyze = consumer.post(f"/consultations/{gastro_id}/analyze")
        analyze.raise_for_status()
        gastro_final = _wait_consultation(consumer, gastro_id, {"ADVICE_READY", "FAILED"})
        assert gastro_final["status"] == "ADVICE_READY", gastro_final
        assert gastro_final["recommended_department_code"] == "GASTROENTEROLOGY"
        gastro_messages = consumer.get(f"/consultations/{gastro_id}/messages")
        gastro_messages.raise_for_status()
        assert any(
            item["sender_type"] == "AI" and (item.get("metadata") or {}).get("advice")
            for item in gastro_messages.json()
        )
        assert any(
            evidence.get("document_id") == acceptance_document_id
            for item in gastro_messages.json()
            for evidence in ((item.get("metadata") or {}).get("advice") or {}).get("evidence", [])
        ), "consumer AI result did not preserve the exact RAG acceptance evidence"

        emergency = consumer.post("/consultations", json={"patient_id": patient_id})
        emergency.raise_for_status()
        emergency_id = emergency.json()["id"]
        emergency_message = consumer.post(
            f"/consultations/{emergency_id}/messages",
            json={
                "client_message_id": f"e1-{suffix}",
                "content": "持续压榨性胸痛、大汗、呼吸困难",
            },
        )
        emergency_message.raise_for_status()
        assert emergency_message.json()["intake"]["risk_level"] == "emergency"
        emergency_messages = consumer.get(f"/consultations/{emergency_id}/messages")
        assert any("120" in item["content"] for item in emergency_messages.json())

        cardio = consumer.post("/consultations", json={"patient_id": patient_id})
        cardio.raise_for_status()
        cardio_id = cardio.json()["id"]
        cardio_message = consumer.post(
            f"/consultations/{cardio_id}/messages",
            json={
                "client_message_id": f"c1-{suffix}",
                "content": "活动后胸痛持续两天，疼痛7分，伴轻微头晕",
            },
        )
        cardio_message.raise_for_status()
        assert cardio_message.json()["intake"]["ready_for_analysis"] is True
        consumer.post(f"/consultations/{cardio_id}/analyze").raise_for_status()
        cardio_final = _wait_consultation(consumer, cardio_id, {"ADVICE_READY", "FAILED"})
        assert cardio_final["status"] == "ADVICE_READY", cardio_final
        assert cardio_final["recommended_department_code"] == "CARDIOLOGY"
        escalated = consumer.post(f"/consultations/{cardio_id}/escalate")
        escalated.raise_for_status()
        escalation = escalated.json()

        settings = get_settings()
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as doctor:
            doctor.post(
                "/api/v1/auth/login",
                json={"account": settings.login_account, "password": settings.login_password},
            ).raise_for_status()
            case = _wait_case(doctor, escalation["case_id"])
            assert case["status"] == "WAITING_REVIEW", case
            assert case["source_channel"] == "wechat_mini_program"
            assert case["visit_id"] == escalation["visit_id"]
            reviewed = doctor.post(
                f"/api/v1/cases/{escalation['case_id']}/review",
                json={"action": "approve", "expected_version": case["assessment_version"]},
            )
            reviewed.raise_for_status()
            assert reviewed.json()["status"] == "FINAL"

        closed = _wait_consultation(consumer, cardio_id, {"CLOSED"})
        assert closed["linked_case_id"] == escalation["case_id"]
        final_messages = consumer.get(f"/consultations/{cardio_id}/messages")
        final_messages.raise_for_status()
        assert any(
            item["sender_type"] == "DOCTOR"
            and (item.get("metadata") or {}).get("doctor_final") is True
            for item in final_messages.json()
        )
        print(
            json.dumps(
                {
                    "consumer_user_id": user_id,
                    "patient_id": patient_id,
                    "gastro_consultation_id": gastro_id,
                    "emergency_consultation_id": emergency_id,
                    "cross_channel_consultation_id": cardio_id,
                    "case_id": escalation["case_id"],
                    "final_status": closed["status"],
                    "doctor_result_returned": True,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
