from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    sex: Literal["male", "female", "other"]
    history: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("birth_date")
    @classmethod
    def birth_date_not_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("出生日期不能晚于今天")
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
