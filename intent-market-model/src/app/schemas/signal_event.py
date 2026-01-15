from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class SignalEventRead(BaseModel):
    id: int
    tenant_id: int
    company_id: int
    source: str
    timestamp: datetime
    signal_type: str
    raw_text: str
    raw_text_uri: str | None
    structured_fields: dict
    diff: dict
    created_at: datetime

    model_config = {"from_attributes": True}
