from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class DoctorIdentity(BaseModel):
    doctor_id: str
    name: str
    department: str
    title: str | None = None
    role: str = "doctor"


class LoginResponse(BaseModel):
    user: DoctorIdentity

