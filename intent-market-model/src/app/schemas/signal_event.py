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
    snippet: str | None
    structured_fields: dict
    diff: dict
    vectorizer_version: str | None
    tokens: list[str]
    drift_score: float | None
    top_terms_delta: list[dict]
    role_bucket_delta: dict
    tech_tag_delta: dict
    created_at: datetime

    model_config = {"from_attributes": True}
