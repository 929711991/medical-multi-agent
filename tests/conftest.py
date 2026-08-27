from collections.abc import Awaitable, Callable

from app.graph.workflow import build_diagnosis_graph
from app.persistence.checkpoint import memory_checkpointer
from app.schemas.diagnosis import DiagnosisResult, PossibleCondition, SpecialistOpinion


async def fake_records(patient_id: str) -> dict:
    return {
        "found": True,
        "patient_id": patient_id,
        "records": {"summary": {"demo": True}, "visits": [], "labs": [], "imaging": []},
    }


async def fake_medical(state: dict, context: dict) -> DiagnosisResult:
    return DiagnosisResult(
        clinical_summary=f"DEMO patient {state['patient_id']}: {state['user_query']}",
        key_findings=[state["user_query"]],
        possible_conditions=[PossibleCondition(name="待鉴别症状", reason="仅基于当前信息", confidence=0.4)],
        red_flags=state.get("red_flags", []),
        missing_information=["需要医生补充查体"],
        recommended_tests=["由医生判断是否需要进一步检查"],
        recommended_department="心内科" if "胸" in state["user_query"] else "消化内科" if "腹" in state["user_query"] else "全科",
        risk_level=state["risk_level"],
        evidence=[],
        rag_enabled=False,
    )


async def fake_cardiology(_: dict) -> SpecialistOpinion:
    return SpecialistOpinion(
        specialty="cardiology",
        summary="心血管专科辅助意见",
        key_findings=["需结合心电图动态变化"],
        differential_directions=[PossibleCondition(name="心源性胸痛待鉴别", reason="存在胸痛描述", confidence=0.5)],
        recommended_tests=["复查心电图"],
    )


async def fake_gastro(_: dict) -> SpecialistOpinion:
    return SpecialistOpinion(
        specialty="gastroenterology",
        summary="消化专科辅助意见",
        key_findings=["需明确腹痛部位"],
        differential_directions=[PossibleCondition(name="消化系统病因待鉴别", reason="存在腹痛", confidence=0.5)],
        recommended_tests=["腹部查体"],
    )


def make_test_graph(checkpointer=None):
    saver = checkpointer or memory_checkpointer()
    return build_diagnosis_graph(
        checkpointer=saver,
        record_loader=fake_records,
        medical_runner=fake_medical,
        cardiology_runner=fake_cardiology,
        gastroenterology_runner=fake_gastro,
    ), saver

