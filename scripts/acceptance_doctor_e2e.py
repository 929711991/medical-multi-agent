import json
import time
from uuid import uuid4

import httpx

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"account": settings.login_account, "password": settings.login_password},
        )
        login.raise_for_status()
        departments = client.get("/api/v1/departments")
        departments.raise_for_status()
        assert any(item["code"] == "CARDIOLOGY" for item in departments.json())
        created = client.post(
            "/api/v1/patients",
            json={
                "name": f"V12实时验收-{uuid4().hex[:8]}",
                "sex": "male",
                "birth_date": "1985-06-01",
                "history": ["高血压病史"],
                "department_code": "CARDIOLOGY",
                "chief_complaint": "活动后胸痛两天",
            },
        )
        created.raise_for_status()
        patient = created.json()
        diagnosis = client.post(
            "/api/v1/diagnoses",
            json={
                "patient_id": patient["patient_id"],
                "visit_id": patient["visit_id"],
                "question": "活动后胸痛两天伴大汗，有高血压史，请评估风险和鉴别方向。",
            },
        )
        diagnosis.raise_for_status()
        case_id = diagnosis.json()["case_id"]
        current = None
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            current = client.get(f"/api/v1/cases/{case_id}")
            current.raise_for_status()
            if current.json()["status"] in {"WAITING_REVIEW", "FAILED"}:
                break
            time.sleep(1)
        assert current is not None
        case = current.json()
        assert case["status"] == "WAITING_REVIEW", case
        assert case["visit_id"] == patient["visit_id"]
        reviewed = client.post(
            f"/api/v1/cases/{case_id}/review",
            json={"action": "approve", "expected_version": case["assessment_version"]},
        )
        reviewed.raise_for_status()
        assert reviewed.json()["status"] == "FINAL"
        history = client.get(f"/api/v1/cases/{case_id}/history")
        history.raise_for_status()
        assert len(history.json()["items"]) >= 5
        print(
            json.dumps(
                {
                    "patient_id": patient["patient_id"],
                    "visit_id": patient["visit_id"],
                    "case_id": case_id,
                    "status": reviewed.json()["status"],
                    "history_count": len(history.json()["items"]),
                    "source_channel": reviewed.json()["source_channel"],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
