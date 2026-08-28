from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    sex: Literal["male", "female", "other"]
    history: list[str] = Field(default_factory=list, max_length=20)
    department_code: str = Field(min_length=2, max_length=64)
    chief_complaint: str = Field(min_length=2, max_length=4000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """清理患者姓名首尾空白并拒绝空姓名。"""
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("birth_date")
    @classmethod
    def birth_date_not_future(cls, value: date | None) -> date | None:
        """拒绝晚于当前日期的出生日期。"""
        if value and value > date.today():
            raise ValueError("出生日期不能晚于今天，请重新选择")
        return value

    @field_validator("department_code")
    @classmethod
    def normalize_department_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("chief_complaint")
    @classmethod
    def normalize_chief_complaint(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("主要主诉不能为空")
        return value


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    sex: Literal["male", "female", "other"] | None = None
    history: list[str] | None = Field(default=None, max_length=20)


class PatientCreateResponse(BaseModel):
    patient_id: str
    name: str
    birth_date: date | None
    sex: str
    history: list[str]
    data_scope: str
    source_channel: str
    visit_id: str
    department_code: str
    department: str
    chief_complaint: str


class VisitCreateRequest(BaseModel):
    department_code: str = Field(min_length=2, max_length=64)
    chief_complaint: str = Field(min_length=2, max_length=4000)
    record: dict[str, Any] = Field(default_factory=dict)

    @field_validator("department_code")
    @classmethod
    def normalize_visit_department(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("chief_complaint")
    @classmethod
    def normalize_visit_complaint(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("主要主诉不能为空")
        return value


class VisitResponse(BaseModel):
    id: str
    patient_id: str
    visit_time: datetime
    department_code: str | None
    department: str
    chief_complaint: str
    record: dict[str, Any]


class PatientSummary(BaseModel):
    found: bool
    patient_id: str
    display_name: str | None = None
    birth_date: date | None = None
    sex: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class TimedRecord(BaseModel):
    record_type: str
    observed_at: datetime
    data: dict[str, Any]
