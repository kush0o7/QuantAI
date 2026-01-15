from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class IntentHypothesisRead(BaseModel):
    id: int
    tenant_id: int
    company_id: int
    intent_type: str
    confidence: float
    evidence: list[dict]
    explanation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IntentSummary(BaseModel):
    investor_summary: list[str]
    jobseeker_summary: str


class IntentDashboardItem(BaseModel):
    intent_type: str
    confidence: float
    explanation: str
    evidence: list[dict]


class IntentDashboard(BaseModel):
    company_id: int
    items: list[IntentDashboardItem]
