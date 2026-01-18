from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class IntentHypothesisRead(BaseModel):
    id: int
    tenant_id: int
    company_id: int
    intent_type: str
    confidence: float
    readiness_score: float | None
    alert_eligible: bool
    alert_reason: str | None
    evidence: list[dict]
    rule_hits_json: list[dict] = Field(default_factory=list)
    explanations_json: list[dict] = Field(default_factory=list)
    explanation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IntentSummary(BaseModel):
    investor_summary: list[str]
    jobseeker_summary: str


class IntentDashboardItem(BaseModel):
    intent_type: str
    confidence: float
    readiness_score: float | None = None
    explanation: str
    evidence: list[dict]


class IntentDashboard(BaseModel):
    company_id: int
    items: list[IntentDashboardItem]
