from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class WeChatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    nickname: str | None = Field(default=None, max_length=120)
    avatar: str | None = Field(default=None, max_length=500)


class H5LoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class ConsumerIdentity(BaseModel):
    user_id: str
    nickname: str | None
    avatar: str | None


class ConsumerLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: ConsumerIdentity


RelationType = Literal["self", "father", "mother", "spouse", "child", "guardian", "other"]


class ConsumerPatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sex: Literal["male", "female", "other"]
    birth_date: date | None = None
    relation_type: RelationType = "self"
    self_reported_history: list[str] = Field(default_factory=list, max_length=20)


class ConsumerPatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    sex: Literal["male", "female", "other"] | None = None
    self_reported_history: list[str] | None = Field(default=None, max_length=20)


class ConsultationCreateRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    consultation_type: str = Field(default="health_advice", min_length=1, max_length=32)


class ConsultationMessageRequest(BaseModel):
    client_message_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)
    content_type: Literal["text"] = "text"

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息内容不能为空")
        return value


class ConsultationMessageResponse(BaseModel):
    id: str
    client_message_id: str
    sender_type: str
    sender_id: str | None
    content_type: str
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime
    duplicate: bool = False


class ConsultationResponse(BaseModel):
    id: str
    patient_id: str
    thread_id: str
    consultation_type: str
    status: str
    risk_level: str | None
    recommended_department_code: str | None
    linked_case_id: str | None
    source_channel: str
    failure_stage: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class ShareCreateRequest(BaseModel):
    permission: Literal["VIEW", "CONTRIBUTE"] = "VIEW"
    expires_in_hours: int = Field(default=24, ge=1, le=720)
    max_uses: int = Field(default=1, ge=1, le=100)


class ShareCreateResponse(BaseModel):
    grant_id: str
    share_token: str
    expires_at: datetime


class ConsentRequest(BaseModel):
    agreement_type: str = Field(min_length=1, max_length=64)
    agreement_version: str = Field(min_length=1, max_length=32)
