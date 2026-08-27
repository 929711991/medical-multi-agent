from app.graph.state import DiagnosisState
from app.schemas.diagnosis import DiagnosisResult, PossibleCondition, SpecialistOpinion


async def synthesis_node(state: DiagnosisState) -> dict:
    draft = DiagnosisResult.model_validate(state["draft_assessment"])
    findings = list(draft.key_findings)
    tests = list(draft.recommended_tests)
    conditions = list(draft.possible_conditions)
    red_flags = list(draft.red_flags)
    for raw in state.get("specialist_opinions", []):
        opinion = SpecialistOpinion.model_validate(raw)
        findings.extend(f"专科意见：{item}" for item in opinion.key_findings)
        tests.extend(opinion.recommended_tests)
        conditions.extend(opinion.differential_directions)
        red_flags.extend(opinion.red_flags)
    synthesized = draft.model_copy(
        update={
            "key_findings": list(dict.fromkeys(findings)),
            "recommended_tests": list(dict.fromkeys(tests)),
            "possible_conditions": _dedupe_conditions(conditions),
            "red_flags": list(dict.fromkeys(red_flags + state.get("red_flags", []))),
            "risk_level": state.get("risk_level", draft.risk_level),
        }
    )
    return {
        "current_stage": "synthesis",
        "draft_assessment": synthesized.model_dump(mode="json"),
        "status": "PENDING_REVIEW",
    }


def _dedupe_conditions(items: list[PossibleCondition]) -> list[PossibleCondition]:
    seen: dict[str, PossibleCondition] = {}
    for item in items:
        existing = seen.get(item.name)
        if existing is None or item.confidence > existing.confidence:
            seen[item.name] = item
    return list(seen.values())

