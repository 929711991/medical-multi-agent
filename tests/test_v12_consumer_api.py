from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.consumer_main import create_consumer_app
from app.core.config import get_settings
from app.persistence.database import get_session_factory
from app.persistence.models import (
    Consultation,
    ConsultationAccessGrant,
    ConsultationMessage,
    ConsultationShareGrant,
    ConsumerPatientRelation,
    ConsumerUser,
    Patient,
)
from app.services.consumer_auth import WeChatSession


class FakeWeChatClient:
    async def exchange_code(self, code: str) -> WeChatSession:
        return WeChatSession(openid=f"test-openid-{code}")


class RecordingQueue:
    def __init__(self) -> None:
        self.consumer_jobs: list[dict] = []
        self.doctor_jobs: list[dict] = []

    async def enqueue_consumer_analysis(self, **payload: str) -> str:
        self.consumer_jobs.append(payload)
        return "consumer-job"

    async def enqueue_doctor_case(self, **payload: str) -> str:
        self.doctor_jobs.append(payload)
        return "doctor-job"


class AllowRateLimiter:
    async def check(self, *_args, **_kwargs) -> int:
        return 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consumer_api_auth_intake_duplicate_access_and_share(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = uuid4().hex
    monkeypatch.setenv("CONSUMER_AUTH_SECRET", f"consumer-secret-{suffix}")
    get_settings.cache_clear()
    queue = RecordingQueue()
    app = create_consumer_app(
        queue=queue, wechat_client=FakeWeChatClient(), rate_limiter=AllowRateLimiter()
    )
    owner_openid = f"test-openid-owner-{suffix}"
    guest_openid = f"test-openid-guest-{suffix}"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://consumer-test"
        ) as client:
            async def login(code: str) -> str:
                response = await client.post(
                    "/api/v1/consumer/auth/wechat", json={"code": code}
                )
                assert response.status_code == 200, response.text
                return response.json()["access_token"]

            owner_token = await login(f"owner-{suffix}")
            guest_token = await login(f"guest-{suffix}")
            owner = {"Authorization": f"Bearer {owner_token}"}
            guest = {"Authorization": f"Bearer {guest_token}"}

            created_patient = await client.post(
                "/api/v1/consumer/patients",
                headers=owner,
                json={
                    "name": "接口测试用户",
                    "sex": "female",
                    "relation_type": "self",
                    "self_reported_history": ["自述高血压"],
                },
            )
            assert created_patient.status_code == 201, created_patient.text
            patient_id = created_patient.json()["patient_id"]
            denied = await client.patch(
                f"/api/v1/consumer/patients/{patient_id}",
                headers=guest,
                json={"name": "越权修改"},
            )
            assert denied.status_code == 403

            consultation = await client.post(
                "/api/v1/consumer/consultations",
                headers=owner,
                json={"patient_id": patient_id},
            )
            assert consultation.status_code == 201, consultation.text
            consultation_id = consultation.json()["id"]

            first = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/messages",
                headers=owner,
                json={"client_message_id": "wx-1", "content": "右下腹越来越疼"},
            )
            assert first.status_code == 200, first.text
            assert first.json()["intake"]["risk_level"] == "medium"
            assert not first.json()["intake"]["ready_for_analysis"]
            duplicate = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/messages",
                headers=owner,
                json={"client_message_id": "wx-1", "content": "重复网络消息"},
            )
            assert duplicate.json()["message"]["duplicate"] is True
            second = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/messages",
                headers=owner,
                json={
                    "client_message_id": "wx-2",
                    "content": "持续两天，疼痛8分，伴有恶心",
                },
            )
            assert second.json()["intake"]["ready_for_analysis"] is True
            analyzed = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/analyze",
                headers=owner,
            )
            assert analyzed.status_code == 202, analyzed.text
            assert len(queue.consumer_jobs) == 1

            share = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/share",
                headers=owner,
                json={"permission": "VIEW", "max_uses": 1, "expires_in_hours": 1},
            )
            assert share.status_code == 200, share.text
            token = share.json()["share_token"]
            grant_id = share.json()["grant_id"]
            redeemed = await client.post(
                f"/api/v1/consumer/shares/{token}/redeem", headers=guest
            )
            assert redeemed.status_code == 200, redeemed.text
            assert (
                await client.get(
                    f"/api/v1/consumer/consultations/{consultation_id}", headers=guest
                )
            ).status_code == 200
            contribute_denied = await client.post(
                f"/api/v1/consumer/consultations/{consultation_id}/messages",
                headers=guest,
                json={"client_message_id": "guest-1", "content": "补充信息"},
            )
            assert contribute_denied.status_code == 403
            assert (
                await client.delete(f"/api/v1/consumer/shares/{grant_id}", headers=owner)
            ).status_code == 204
            assert (
                await client.get(
                    f"/api/v1/consumer/consultations/{consultation_id}", headers=guest
                )
            ).status_code == 403

            emergency_consultation = await client.post(
                "/api/v1/consumer/consultations",
                headers=owner,
                json={"patient_id": patient_id},
            )
            emergency_id = emergency_consultation.json()["id"]
            emergency = await client.post(
                f"/api/v1/consumer/consultations/{emergency_id}/messages",
                headers=owner,
                json={
                    "client_message_id": "emergency-1",
                    "content": "持续压榨性胸痛、大汗、呼吸困难",
                },
            )
            assert emergency.json()["intake"]["risk_level"] == "emergency"
            messages = await client.get(
                f"/api/v1/consumer/consultations/{emergency_id}/messages", headers=owner
            )
            assert any("120" in item["content"] for item in messages.json())
            assert len(queue.consumer_jobs) == 1
    finally:
        async with get_session_factory()() as session:
            users = (
                await session.scalars(
                    select(ConsumerUser).where(
                        ConsumerUser.openid.in_([owner_openid, guest_openid])
                    )
                )
            ).all()
            user_ids = [item.id for item in users]
            relation_rows = (
                await session.scalars(
                    select(ConsumerPatientRelation).where(
                        ConsumerPatientRelation.consumer_user_id.in_(user_ids)
                    )
                )
            ).all() if user_ids else []
            patient_ids = [item.patient_id for item in relation_rows]
            consultation_ids = list(
                (
                    await session.scalars(
                        select(Consultation.id).where(Consultation.consumer_user_id.in_(user_ids))
                    )
                ).all()
            ) if user_ids else []
            if consultation_ids:
                await session.execute(delete(ConsultationAccessGrant).where(ConsultationAccessGrant.consultation_id.in_(consultation_ids)))
                await session.execute(delete(ConsultationMessage).where(ConsultationMessage.consultation_id.in_(consultation_ids)))
                await session.execute(delete(ConsultationShareGrant).where(ConsultationShareGrant.consultation_id.in_(consultation_ids)))
                await session.execute(delete(Consultation).where(Consultation.id.in_(consultation_ids)))
            if user_ids:
                await session.execute(delete(ConsumerPatientRelation).where(ConsumerPatientRelation.consumer_user_id.in_(user_ids)))
            if patient_ids:
                await session.execute(delete(Patient).where(Patient.id.in_(patient_ids)))
            if user_ids:
                await session.execute(delete(ConsumerUser).where(ConsumerUser.id.in_(user_ids)))
            await session.commit()
        get_settings.cache_clear()
