from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.timeline import (
    IntentTimeline,
    IntentTimelinePoint,
    IntentTimelineSeries,
    ReadinessTimeline,
    ReadinessTimelinePoint,
)
from app.services.cache_service import get_cached_response, set_cached_response
from data.storage.db import SignalEvent, get_session
from data.storage.repositories import company_repo, intents_repo

router = APIRouter()


@router.get("/tenants/{tenant_id}/companies/{company_id}/intents/timeline", response_model=IntentTimeline)
def intent_timeline(
    tenant_id: int,
    company_id: int,
    days: int = Query(default=365, ge=30, le=1095),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    cache_key = f"timeline:{tenant_id}:{company_id}:{days}"
    cached = get_cached_response(session, cache_key)
    if cached:
        return cached
    since = datetime.now(timezone.utc) - timedelta(days=days)
    intents = intents_repo.list_intents_since(session, tenant_id, company_id, since)
    series_map: dict[str, list[IntentTimelinePoint]] = {}
    for intent in intents:
        series_map.setdefault(intent.intent_type, []).append(
            IntentTimelinePoint(timestamp=intent.created_at, confidence=intent.confidence)
        )
    series = [
        IntentTimelineSeries(intent_type=key, points=value) for key, value in series_map.items()
    ]
    payload = IntentTimeline(company_id=company_id, series=series).model_dump(mode="json")
    set_cached_response(session, cache_key, payload)
    return payload


@router.get(
    "/tenants/{tenant_id}/companies/{company_id}/timeline/ipo_prep",
    response_model=ReadinessTimeline,
)
def ipo_prep_timeline(
    tenant_id: int,
    company_id: int,
    days: int = Query(default=365, ge=30, le=1095),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    cache_key = f"timeline:ipo_prep:{tenant_id}:{company_id}:{days}"
    cached = get_cached_response(session, cache_key)
    if cached:
        return cached
    since = datetime.now(timezone.utc) - timedelta(days=days)
    intents = intents_repo.list_intents_since(
        session, tenant_id, company_id, since, intent_type="IPO_PREP"
    )
    signal_ids = [
        int(item.get("signal_event_id"))
        for intent in intents
        for item in (intent.evidence or [])
        if item.get("signal_event_id") is not None
    ]
    signals = []
    if signal_ids:
        signals = list(
            session.query(SignalEvent).filter(SignalEvent.id.in_(signal_ids)).all()
        )
    signal_by_id = {signal.id: signal for signal in signals}
    points: list[ReadinessTimelinePoint] = []
    for intent in intents:
        signal_id = None
        if intent.evidence:
            signal_id = intent.evidence[0].get("signal_event_id")
        drift_score = None
        if signal_id and signal_id in signal_by_id:
            signal = signal_by_id[signal_id]
            drift_score = signal.drift_score or signal.diff.get("drift_score")
        points.append(
            ReadinessTimelinePoint(
                timestamp=intent.created_at,
                readiness_score=intent.readiness_score,
                confidence=intent.confidence,
                drift_score=drift_score,
                rule_hits=len(intent.rule_hits_json or []),
            )
        )
    payload = ReadinessTimeline(
        company_id=company_id, intent_type="IPO_PREP", points=points
    ).model_dump(mode="json")
    set_cached_response(session, cache_key, payload)
    return payload
