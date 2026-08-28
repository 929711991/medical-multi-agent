import logging
from datetime import date
from time import perf_counter
from typing import Any

from app.persistence.database import get_session_factory
from app.persistence.repositories import DoctorRepository, PatientRepository

logger = logging.getLogger("medical.mcp")


async def _patient_call(patient_id: str, method: str) -> dict[str, Any]:
    """统一执行患者查询，隔离数据库异常并记录工具耗时。"""
    started = perf_counter()
    status = "成功"
    tool_name = {
        "summary": "get_patient_summary",
        "visits": "get_patient_visits",
        "all_records": "get_medical_records",
        "labs": "get_lab_results",
        "imaging": "get_imaging_reports",
        "medications": "get_medications",
        "allergies": "get_allergies",
    }.get(method, method)
    try:
        # MCP 只允许调用仓储层的既定查询方法，避免把任意数据库操作暴露给智能体。
        async with get_session_factory()() as session:
            repository = PatientRepository(session)
            return await getattr(repository, method)(patient_id)
    except Exception as exc:
        status = "失败"
        return {
            "found": False,
            "patient_id": patient_id,
            "error": "database_unavailable",
            "message": f"患者数据库操作失败：{type(exc).__name__}",
        }
    finally:
        logger.info(
            "患者 MCP 工具执行完成",
            extra={
                "tool_name": tool_name,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": status,
            },
        )


async def get_patient_summary(patient_id: str) -> dict[str, Any]:
    """返回患者的最小人口学信息和病史摘要。"""
    return await _patient_call(patient_id, "summary")


async def get_patient_visits(patient_id: str) -> dict[str, Any]:
    """按时间倒序返回历史就诊，并保留 visit_time。"""
    return await _patient_call(patient_id, "visits")


async def get_medical_records(patient_id: str) -> dict[str, Any]:
    """返回患者当前全部病历分类。"""
    return await _patient_call(patient_id, "all_records")


async def get_lab_results(patient_id: str) -> dict[str, Any]:
    """返回检验结果及其 observed_at。"""
    return await _patient_call(patient_id, "labs")


async def get_imaging_reports(patient_id: str) -> dict[str, Any]:
    """返回影像报告及其 observed_at。"""
    return await _patient_call(patient_id, "imaging")


async def get_medications(patient_id: str) -> dict[str, Any]:
    """返回已记录的用药史；V1.1 不通过该工具开具处方。"""
    return await _patient_call(patient_id, "medications")


async def get_allergies(patient_id: str) -> dict[str, Any]:
    """返回已记录的过敏史及可用的观察时间。"""
    return await _patient_call(patient_id, "allergies")


async def create_patient(
    name: str,
    sex: str,
    birth_date: str | None = None,
    history: list[str] | None = None,
    source_channel: str = "mcp",
) -> dict[str, Any]:
    """受控创建患者；patient_id 由后端生成，不接受调用方指定。"""
    if sex not in {"male", "female", "other"}:
        return {"created": False, "error": "invalid_sex", "message": "sex 必须为 male/female/other"}
    parsed_birth_date = date.fromisoformat(birth_date) if birth_date else None
    async with get_session_factory()() as session:
        patient = await PatientRepository(session).create(
            name=name,
            birth_date=parsed_birth_date,
            sex=sex,
            history=history or [],
            data_scope="sandbox",
            source_channel=source_channel,
        )
        return {
            "created": True,
            "patient_id": str(patient.id),
            "name": patient.display_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
            "sex": patient.sex,
            "history": patient.summary_json.get("history", []),
            "data_scope": patient.data_scope,
            "source_channel": patient.source_channel,
        }


async def update_patient(
    patient_id: str,
    name: str | None = None,
    sex: str | None = None,
    birth_date: str | None = None,
    history: list[str] | None = None,
) -> dict[str, Any]:
    """受控修改患者基础资料和病史摘要；不允许越过 data_scope 修改非授权患者。"""
    if sex is not None and sex not in {"male", "female", "other"}:
        return {"updated": False, "patient_id": patient_id, "error": "invalid_sex"}
    parsed_birth_date = date.fromisoformat(birth_date) if birth_date else None
    async with get_session_factory()() as session:
        repository = PatientRepository(session)
        if await repository.data_scope(patient_id) != "sandbox":
            return {"updated": False, "patient_id": patient_id, "error": "patient_not_found"}
        patient = await repository.update_patient(
            patient_id,
            name=name,
            birth_date=parsed_birth_date,
            sex=sex,
            history=history,
        )
        if patient is None:
            return {"updated": False, "patient_id": patient_id, "error": "patient_not_found"}
        result = await repository.summary(patient_id)
        result["updated"] = True
        return result


async def get_doctor_info(doctor_id: str) -> dict[str, Any]:
    """返回医生的公开执业信息。"""
    started = perf_counter()
    status = "成功"
    try:
        async with get_session_factory()() as session:
            return await DoctorRepository(session).info(doctor_id)
    except Exception as exc:
        status = "失败"
        return {
            "found": False,
            "doctor_id": doctor_id,
            "error": "database_unavailable",
            "message": f"医生数据库查询失败：{type(exc).__name__}",
        }
    finally:
        logger.info(
            "医生 MCP 工具执行完成",
            extra={
                "tool_name": "get_doctor_info",
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": status,
            },
        )
