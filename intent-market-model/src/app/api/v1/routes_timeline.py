from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.timeline import IntentTimeline, IntentTimelinePoint, IntentTimelineSeries
from data.storage.db import get_session
from data.storage.repositories import company_repo, intents_repo

router = APIRouter()


@router.get("/tenants/{tenant_id}/companies/{company_id}/intents/timeline", response_model=IntentTimeline)
def intent_timeline(
    tenant_id: int,
    company_id: int,
    days: int = Query(default=365, ge=30, le=730),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    since = datetime.now(timezone.utc) - timedelta(days=days)
    intents = intents_repo.list_intents_since(session, tenant_id, company_id, since)
    series_map: dict[str, list[IntentTimelinePoint]] = {}
    for intent in intents:
        series_map.setdefault(intent.intent_type, []).append(
            IntentTimelinePoint(timestamp=intent.created_at, confidence=intent.confidence)
        )
    series = [IntentTimelineSeries(intent_type=key, points=value) for key, value in series_map.items()]
    return IntentTimeline(company_id=company_id, series=series)
