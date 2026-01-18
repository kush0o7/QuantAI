from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ExplainRuleHit(BaseModel):
    rule_name: str
    weight: float
    signal_type: str
    match: str
    snippet: str
    source_snippet: str


class ExplainDriftDelta(BaseModel):
    term: str
    delta: float


class ExplainSourceSnippet(BaseModel):
    signal_event_id: int
    source: str
    signal_type: str
    timestamp: datetime
    snippet: str


class ExplainResponse(BaseModel):
    company_id: int
    intent_type: str
    confidence: float
    readiness_score: float | None
    alert_eligible: bool
    alert_reason: str | None
    rule_hits: list[ExplainRuleHit] = Field(default_factory=list)
    drift_deltas: list[ExplainDriftDelta] = Field(default_factory=list)
    source_snippets: list[ExplainSourceSnippet] = Field(default_factory=list)
    created_at: datetime
