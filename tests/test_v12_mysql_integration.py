from datetime import UTC, datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, func, select

from app.core.snowflake import generate_snowflake_id
from app.persistence.consumer_repositories import (
    ConsentRepository,
    ConsultationRepository,
    ConsumerPatientRelationRepository,
    ConsumerUserRepository,
    ShareGrantRepository,
)
from app.persistence.database import get_session_factory
from app.persistence.models import (
    Consultation,
    ConsultationAccessGrant,
    ConsultationMessage,
    ConsultationShareGrant,
    ConsumerConsentRecord,
    ConsumerPatientRelation,
    ConsumerUser,
    MedicalAssessment,
    MedicalCase,
    MedicalVisit,
    Patient,
)
from app.persistence.repositories import CaseRepository, PatientRepository
from app.services.consumer_access import ConsumerPatientAccessService
from app.services.consumer_patient import ConsumerPatientService
from app.services.patient_service import PatientService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_v12_real_mysql_patient_consumer_share_and_case(monkeypatch: pytest.MonkeyPatch) -> None:
    suffix = uuid4().hex
    ids: dict[str, list[int]] = {
        "patients": [],
        "users": [],
        "consultations": [],
        "cases": [],
        "visits": [],
        "shares": [],
    }
    try:
        async with get_session_factory()() as session:
            patient, visit = await PatientService(session).create_patient_with_visit(
                name=f"V12医生患者-{suffix}",
                birth_date=None,
                sex="other",
                history=[],
                department_code="GENERAL",
                chief_complaint="头晕一天",
            )
            ids["patients"].append(patient.id)
            ids["visits"].append(visit.id)
            assert visit.patient_id == patient.id
            assert visit.department_code == "GENERAL"

            second = await PatientService(session).create_visit(
                patient_id=str(patient.id),
                department_code="CARDIOLOGY",
                chief_complaint="活动后胸痛",
            )
            ids["visits"].append(second.id)

            case_id = str(generate_snowflake_id())
            case = await CaseRepository(session).create(
                case_id=case_id,
                patient_id=str(patient.id),
                thread_id=case_id,
                question="胸痛风险评估",
                visit_id=str(second.id),
                status="QUEUED",
            )
            ids["cases"].append(case.id)
            assert case.visit_id == second.id
            assert await CaseRepository(session).claim_ai_run(case_id)
            assert not await CaseRepository(session).claim_ai_run(case_id)

            rollback_name = f"V12回滚-{suffix}"
            service = PatientService(session)
            monkeypatch.setattr(
                service.patients,
                "create_visit",
                AsyncMock(side_effect=RuntimeError("forced visit failure")),
            )
            with pytest.raises(RuntimeError):
                await service.create_patient_with_visit(
                    name=rollback_name,
                    birth_date=None,
                    sex="other",
                    history=[],
                    department_code="GENERAL",
                    chief_complaint="测试回滚",
                )
            assert (
                await session.scalar(
                    select(func.count()).select_from(Patient).where(Patient.display_name == rollback_name)
                )
            ) == 0

            users = ConsumerUserRepository(session)
            owner = await users.create_or_update(
                openid=f"openid-owner-{suffix}", unionid=None, nickname="甲", avatar=None
            )
            guest = await users.create_or_update(
                openid=f"openid-guest-{suffix}", unionid=None, nickname="乙", avatar=None
            )
            ids["users"].extend([owner.id, guest.id])
            consumer_patient = await ConsumerPatientService(session).create_profile(
                user_id=str(owner.id),
                name=f"V12消费者-{suffix}",
                sex="female",
                birth_date=None,
                relation_type="self",
                self_reported_history=["自述高血压"],
            )
            ids["patients"].append(consumer_patient.id)
            assert consumer_patient.data_scope == "consumer"
            assert consumer_patient.summary_json["self_reported_history"] == ["自述高血压"]
            assert not await ConsumerPatientAccessService(session).can_access_patient(
                str(guest.id), str(consumer_patient.id)
            )

            consultation = await ConsultationRepository(session).create(
                user_id=owner.id,
                patient_id=consumer_patient.id,
                consultation_type="health_advice",
            )
            ids["consultations"].append(consultation.id)
            first, inserted = await ConsultationRepository(session).add_message(
                consultation_id=consultation.id,
                client_message_id="wx-retry-1",
                sender_type="PATIENT",
                sender_id=owner.id,
                content="右下腹越来越疼",
            )
            duplicate, inserted_again = await ConsultationRepository(session).add_message(
                consultation_id=consultation.id,
                client_message_id="wx-retry-1",
                sender_type="PATIENT",
                sender_id=owner.id,
                content="不会重复写入",
            )
            assert inserted and not inserted_again and first.id == duplicate.id

            token_hash = "a" * 64
            share = await ShareGrantRepository(session).create(
                consultation_id=consultation.id,
                created_by=owner.id,
                token_hash=token_hash,
                permission="VIEW",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                max_uses=1,
            )
            ids["shares"].append(share.id)
            await ShareGrantRepository(session).redeem(token_hash, guest.id)
            assert await ConsultationRepository(session).can_access(consultation.id, guest.id)
            assert await ShareGrantRepository(session).revoke(share.id, owner.id)
            assert not await ConsultationRepository(session).can_access(consultation.id, guest.id)

            expired = await ShareGrantRepository(session).create(
                consultation_id=consultation.id,
                created_by=owner.id,
                token_hash="b" * 64,
                permission="VIEW",
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
                max_uses=1,
            )
            ids["shares"].append(expired.id)
            with pytest.raises(LookupError, match="SHARE_TOKEN_EXPIRED"):
                await ShareGrantRepository(session).redeem("b" * 64, guest.id)

            consent = await ConsentRepository(session).record(owner.id, "privacy", "1.2")
            assert consent.agreement_version == "1.2"
    finally:
        async with get_session_factory()() as cleanup:
            if ids["consultations"]:
                await cleanup.execute(
                    delete(ConsultationAccessGrant).where(
                        ConsultationAccessGrant.consultation_id.in_(ids["consultations"])
                    )
                )
                await cleanup.execute(
                    delete(ConsultationMessage).where(
                        ConsultationMessage.consultation_id.in_(ids["consultations"])
                    )
                )
                await cleanup.execute(
                    delete(ConsultationShareGrant).where(
                        ConsultationShareGrant.consultation_id.in_(ids["consultations"])
                    )
                )
                await cleanup.execute(
                    delete(Consultation).where(Consultation.id.in_(ids["consultations"]))
                )
            if ids["users"]:
                await cleanup.execute(
                    delete(ConsumerConsentRecord).where(
                        ConsumerConsentRecord.consumer_user_id.in_(ids["users"])
                    )
                )
                await cleanup.execute(
                    delete(ConsumerPatientRelation).where(
                        ConsumerPatientRelation.consumer_user_id.in_(ids["users"])
                    )
                )
            if ids["cases"]:
                await cleanup.execute(delete(MedicalAssessment).where(MedicalAssessment.case_id.in_(ids["cases"])))
                await cleanup.execute(delete(MedicalCase).where(MedicalCase.id.in_(ids["cases"])))
            if ids["visits"]:
                await cleanup.execute(delete(MedicalVisit).where(MedicalVisit.id.in_(ids["visits"])))
            if ids["patients"]:
                await cleanup.execute(delete(Patient).where(Patient.id.in_(ids["patients"])))
            if ids["users"]:
                await cleanup.execute(delete(ConsumerUser).where(ConsumerUser.id.in_(ids["users"])))
            await cleanup.commit()
