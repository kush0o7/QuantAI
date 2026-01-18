from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    domain: str | None = None
    greenhouse_board: str | None = None


class CompanyRead(BaseModel):
    id: int
    tenant_id: int
    name: str
    domain: str | None
    greenhouse_board: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
