from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class OutcomeCreate(BaseModel):
    outcome_type: str
    timestamp: datetime
    source: str
    details: dict | None = None


class OutcomeRead(BaseModel):
    id: int
    tenant_id: int
    company_id: int
    outcome_type: str
    timestamp: datetime
    source: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}
