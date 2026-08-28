from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from app.api.consumer.sharing import _hash
from app.core.config import get_settings
from app.persistence.models import ConsumerPatientRelation
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.patient import PatientCreateRequest, VisitCreateRequest
from app.services.consumer_access import ConsumerPatientAccessService
from app.services.consumer_advice import ConsumerAdviceAssembler, MedicationSafetyGuard
from app.services.consumer_auth import decode_consumer_token, issue_consumer_token
from app.services.consumer_consultation import ConsultationStateMachine
from app.services.consumer_intake import ConsumerIntakeAgent, DepartmentResolver


def test_patient_and_visit_v12_validation() -> None:
    payload = PatientCreateRequest(
        name=" 张某 ",
        sex="female",
        birth_date=date(1990, 1, 1),
        history=["高血压"],
        department_code="cardiology",
        chief_complaint=" 活动后胸痛两天 ",
    )
    assert payload.name == "张某"
    assert payload.department_code == "CARDIOLOGY"
    assert payload.chief_complaint == "活动后胸痛两天"
    assert VisitCreateRequest(
        department_code="general", chief_complaint="头晕"
    ).department_code == "GENERAL"
    with pytest.raises(ValueError):
        PatientCreateRequest(
            name="张某",
            sex="female",
            birth_date=date.today() + timedelta(days=1),
            department_code="GENERAL",
            chief_complaint="头晕",
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("持续压榨性胸痛、大汗、呼吸困难", "emergency"),
        ("右下腹越来越疼", "medium"),
        ("轻微鼻塞", "low"),
    ],
)
def test_consumer_intake_runs_deterministic_risk(text: str, expected: str) -> None:
    assert ConsumerIntakeAgent.assess([text]).risk_level == expected


def test_consumer_intake_structured_followup_then_ready() -> None:
    first = ConsumerIntakeAgent.assess(["右下腹越来越疼"])
    assert not first.ready_for_analysis
    assert first.next_question
    second = ConsumerIntakeAgent.assess(
        ["右下腹越来越疼", "已经持续两天，疼痛8分，伴有恶心"]
    )
    assert second.ready_for_analysis
    assert second.information_completeness == 100


def test_department_resolver_is_independent_of_visit_department() -> None:
    assert DepartmentResolver.resolve("活动后胸痛", "消化内科") == "CARDIOLOGY"
    assert DepartmentResolver.resolve("右下腹疼痛伴恶心") == "GASTROENTEROLOGY"
    assert DepartmentResolver.resolve("皮疹") == "GENERAL"


def test_consumer_advice_and_medication_safety() -> None:
    result = DiagnosisResult(
        clinical_summary="需要进一步评估腹痛原因",
        recommended_department="消化内科",
        recommended_tests=["腹部查体"],
        risk_level="medium",
    )
    advice = ConsumerAdviceAssembler.assemble(result, "右下腹疼痛")
    assert advice.recommended_department_code == "GASTROENTEROLOGY"
    assert "不替代医生" in advice.disclaimer
    guarded = MedicationSafetyGuard.sanitize(["某药每日10mg", "保持充足休息"])
    assert all("10mg" not in item for item in guarded)
    assert any("咨询医生或药师" in item for item in guarded)


def test_consultation_state_transitions() -> None:
    ConsultationStateMachine.validate("CREATED", "WAITING_USER")
    ConsultationStateMachine.validate("READY_ANALYSIS", "ANALYZING")
    with pytest.raises(ValueError, match="CONSULTATION_INVALID_STATE"):
        ConsultationStateMachine.validate("CLOSED", "ANALYZING")


@pytest.mark.asyncio
async def test_consumer_patient_access_permission_rank() -> None:
    service = ConsumerPatientAccessService(AsyncMock())
    service.relations.get = AsyncMock(
        return_value=ConsumerPatientRelation(
            consumer_user_id=1,
            patient_id=2,
            relation_type="self",
            permission="CONTRIBUTE",
            status="ACTIVE",
        )
    )
    assert await service.can_access_patient("1", "2", "VIEW")
    assert not await service.can_access_patient("1", "2", "MANAGE")


def test_share_hash_never_contains_plain_token() -> None:
    token = "plain-secret-share-token"
    digest = _hash(token)
    assert token not in digest
    assert len(digest) == 64
    assert digest == _hash(token)


def test_consumer_token_is_separate_and_signed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONSUMER_AUTH_SECRET", "unit-test-consumer-secret")
    get_settings.cache_clear()
    token, expires_in = issue_consumer_token("123")
    assert decode_consumer_token(token)["sub"] == "123"
    assert expires_in > 0
    with pytest.raises(ValueError):
        decode_consumer_token(token + "tampered")
    get_settings.cache_clear()
