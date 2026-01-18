from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    rate_limit_per_min: int | None = None


class ApiKeyCreated(BaseModel):
    id: int
    tenant_id: int
    name: str
    key: str
    rate_limit_per_min: int
    created_at: datetime


class ApiKeyRead(BaseModel):
    id: int
    tenant_id: int
    name: str
    rate_limit_per_min: int
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
