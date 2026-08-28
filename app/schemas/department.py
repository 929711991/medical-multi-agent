from datetime import datetime

from pydantic import BaseModel


class DepartmentResponse(BaseModel):
    code: str
    name: str
    enabled: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
