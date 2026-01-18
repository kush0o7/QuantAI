from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class IntentTimelinePoint(BaseModel):
    timestamp: datetime
    confidence: float


class IntentTimelineSeries(BaseModel):
    intent_type: str
    points: list[IntentTimelinePoint]


class IntentTimeline(BaseModel):
    company_id: int
    series: list[IntentTimelineSeries]


class ReadinessTimelinePoint(BaseModel):
    timestamp: datetime
    readiness_score: float | None
    confidence: float
    drift_score: float | None
    rule_hits: int


class ReadinessTimeline(BaseModel):
    company_id: int
    intent_type: str
    points: list[ReadinessTimelinePoint]
