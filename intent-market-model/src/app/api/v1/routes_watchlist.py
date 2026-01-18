from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.watchlist import WatchlistItem, WatchlistResponse
from data.storage.db import get_session
from data.storage.repositories import company_repo, intents_repo, signals_repo, tenant_repo

router = APIRouter()


@router.get("/tenants/{tenant_id}/watchlist", response_model=WatchlistResponse)
def watchlist(tenant_id: int, session: Session = Depends(get_session)):
    tenant = tenant_repo.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    companies = company_repo.list_companies(session, tenant_id)
    items: list[WatchlistItem] = []
    for company in companies:
        intents = intents_repo.list_latest_intents(
            session, tenant_id, company.id, limit=2, intent_types=["IPO_PREP"]
        )
        readiness_score = None
        score_delta = None
        confidence = None
        alert_eligible = False
        alert_reason = None
        top_rule_hits: list[str] = []
        if intents:
            readiness_score = intents[0].readiness_score
            confidence = intents[0].confidence
            alert_eligible = bool(intents[0].alert_eligible)
            alert_reason = intents[0].alert_reason
            top_rule_hits = [hit.get("rule_name") for hit in intents[0].rule_hits_json or []][:3]
        if len(intents) >= 2 and intents[0].readiness_score is not None:
            prev_score = intents[1].readiness_score or 0.0
            score_delta = intents[0].readiness_score - prev_score
        last_signal = signals_repo.list_recent_signals(session, tenant_id, company.id, limit=1)
        last_signal_date = last_signal[0].timestamp if last_signal else None
        items.append(
            WatchlistItem(
                company_id=company.id,
                company_name=company.name,
                readiness_score=readiness_score,
                score_delta=score_delta,
                confidence=confidence,
                alert_eligible=alert_eligible,
                alert_reason=alert_reason,
                last_signal_date=last_signal_date,
                top_rule_hits=[item for item in top_rule_hits if item],
            )
        )
    return WatchlistResponse(tenant_id=tenant_id, items=items)
