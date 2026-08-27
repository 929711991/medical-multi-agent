from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class PatientSummary(BaseModel):
    found: bool
    patient_id: str
    demo_label: str | None = None
    birth_date: date | None = None
    sex: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class TimedRecord(BaseModel):
    record_type: str
    observed_at: datetime
    data: dict[str, Any]

