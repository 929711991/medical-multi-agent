import logging
from time import perf_counter
from typing import Any

from app.persistence.database import get_session_factory
from app.persistence.repositories import DoctorRepository, PatientRepository

logger = logging.getLogger("medical.mcp")


async def _patient_call(patient_id: str, method: str) -> dict[str, Any]:
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
        async with get_session_factory()() as session:
            repository = PatientRepository(session)
            return await getattr(repository, method)(patient_id)
    except Exception as exc:
        status = "失败"
        return {
            "found": False,
            "patient_id": patient_id,
            "error": "database_unavailable",
            "message": f"患者数据库查询失败：{type(exc).__name__}",
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
    """返回虚构 DEMO 患者的最小人口学信息和病史摘要。"""
    return await _patient_call(patient_id, "summary")


async def get_patient_visits(patient_id: str) -> dict[str, Any]:
    """按时间倒序返回历史就诊，并保留 visit_time。"""
    return await _patient_call(patient_id, "visits")


async def get_medical_records(patient_id: str) -> dict[str, Any]:
    """返回患者所有只读病历分类。"""
    return await _patient_call(patient_id, "all_records")


async def get_lab_results(patient_id: str) -> dict[str, Any]:
    """返回检验结果及其 observed_at。"""
    return await _patient_call(patient_id, "labs")


async def get_imaging_reports(patient_id: str) -> dict[str, Any]:
    """返回影像报告及其 observed_at。"""
    return await _patient_call(patient_id, "imaging")


async def get_medications(patient_id: str) -> dict[str, Any]:
    """返回用药史；本工具不能开具处方或修改数据。"""
    return await _patient_call(patient_id, "medications")


async def get_allergies(patient_id: str) -> dict[str, Any]:
    """返回已记录的过敏史及可用的观察时间。"""
    return await _patient_call(patient_id, "allergies")


async def get_doctor_info(doctor_id: str) -> dict[str, Any]:
    """返回 DEMO 医生的公开执业信息。"""
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
