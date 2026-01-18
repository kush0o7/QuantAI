from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    company_id: int
    company_name: str
    readiness_score: float | None
    score_delta: float | None
    confidence: float | None
    alert_eligible: bool
    alert_reason: str | None
    last_signal_date: datetime | None
    top_rule_hits: list[str] = Field(default_factory=list)


class WatchlistResponse(BaseModel):
    tenant_id: int
    items: list[WatchlistItem]
