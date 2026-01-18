from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.intent import IntentDashboard, IntentDashboardItem, IntentHypothesisRead, IntentSummary
from app.services.cache_service import get_cached_response, set_cached_response
from app.services.translator_service import TranslatorService
from data.storage.db import get_session
from data.storage.repositories import company_repo, intents_repo

router = APIRouter()


@router.get("/{company_id}/intents/latest", response_model=dict)
def latest_intents(
    tenant_id: int,
    company_id: int,
    intent_type: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    intent_types = None
    if intent_type:
        intent_types = [item.strip() for item in intent_type.split(",") if item.strip()]
    intents = intents_repo.list_latest_intents(
        session,
        tenant_id,
        company_id,
        limit=limit,
        intent_types=intent_types,
        min_confidence=min_confidence,
    )
    translator = TranslatorService()
    summaries = translator.summarize(intents)
    return {
        "intents": [IntentHypothesisRead.model_validate(intent) for intent in intents],
        "summaries": IntentSummary(**summaries),
    }


@router.get("/{company_id}/intents/dashboard", response_model=IntentDashboard)
def intent_dashboard(tenant_id: int, company_id: int, session: Session = Depends(get_session)):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    cache_key = f"dashboard:{tenant_id}:{company_id}"
    cached = get_cached_response(session, cache_key)
    if cached:
        return cached
    intents = intents_repo.list_latest_intents(session, tenant_id, company_id, limit=100)
    items: dict[str, IntentDashboardItem] = {}
    for intent in intents:
        existing = items.get(intent.intent_type)
        if existing and existing.confidence >= intent.confidence:
            continue
        items[intent.intent_type] = IntentDashboardItem(
            intent_type=intent.intent_type,
            confidence=intent.confidence,
            readiness_score=intent.readiness_score,
            explanation=intent.explanation,
            evidence=intent.evidence or [],
        )
    payload = IntentDashboard(
        company_id=company_id, items=list(items.values())
    ).model_dump(mode="json")
    set_cached_response(session, cache_key, payload)
    return payload
