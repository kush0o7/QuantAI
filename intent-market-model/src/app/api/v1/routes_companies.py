from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.signal_harvester.agent import SignalHarvesterAgent
from agents.intent_inference.agent import IntentInferenceAgent
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.explain import ExplainResponse
from app.schemas.signal_event import SignalEventRead
from app.services.cache_service import invalidate_cache_prefix
from data.storage.db import SignalEvent, get_session
from data.storage.repositories import company_repo, intents_repo, signals_repo

router = APIRouter()


@router.post("/", response_model=CompanyRead)
def create_company(
    tenant_id: int,
    payload: CompanyCreate,
    session: Session = Depends(get_session),
):
    company = company_repo.create_company(
        session,
        tenant_id,
        payload.name,
        payload.domain,
        payload.greenhouse_board,
    )
    return company


@router.get("/", response_model=list[CompanyRead])
def list_companies(tenant_id: int, session: Session = Depends(get_session)):
    return company_repo.list_companies(session, tenant_id)


@router.post("/ingest/{company_id}")
def ingest_company_signals(
    tenant_id: int,
    company_id: int,
    source: str = Query(default="mock"),
    infer: bool = Query(default=True),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    harvester = SignalHarvesterAgent(session)
    inserted = harvester.harvest(company, source)
    intents_created = 0
    if infer:
        recent_signals = signals_repo.list_recent_signals(
            session, tenant_id, company_id, limit=50
        )
        inferencer = IntentInferenceAgent(session)
        intents_created = len(inferencer.infer(recent_signals))
    invalidate_cache_prefix(session, f"dashboard:{tenant_id}:{company_id}")
    invalidate_cache_prefix(session, f"timeline:{tenant_id}:{company_id}")
    invalidate_cache_prefix(session, f"timeline:ipo_prep:{tenant_id}:{company_id}")
    return {"inserted": inserted, "intents_created": intents_created}


@router.get("/{company_id}/signals/recent", response_model=list[SignalEventRead])
def recent_signals(tenant_id: int, company_id: int, session: Session = Depends(get_session)):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return signals_repo.list_recent_signals(session, tenant_id, company_id)


@router.get("/{company_id}/explain", response_model=ExplainResponse)
def explain_company(tenant_id: int, company_id: int, session: Session = Depends(get_session)):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    intents = intents_repo.list_latest_intents(
        session, tenant_id, company_id, limit=1, intent_types=["IPO_PREP"]
    )
    if not intents:
        raise HTTPException(status_code=404, detail="No IPO_PREP intent found")
    intent = intents[0]
    evidence = intent.evidence or []
    signal_ids = [
        int(item["signal_event_id"])
        for item in evidence
        if item.get("signal_event_id") is not None
    ]
    signals: list[SignalEvent] = []
    if signal_ids:
        signals = list(
            session.execute(select(SignalEvent).where(SignalEvent.id.in_(signal_ids)))
            .scalars()
            .all()
        )
    signal_by_id = {signal.id: signal for signal in signals}
    source_snippets = []
    for signal_id in signal_ids:
        signal = signal_by_id.get(signal_id)
        if not signal:
            continue
        snippet = signal.snippet or signal.raw_text[:200]
        source_snippets.append(
            {
                "signal_event_id": signal.id,
                "source": signal.source,
                "signal_type": signal.signal_type,
                "timestamp": signal.timestamp,
                "snippet": snippet,
            }
        )

    drift_deltas = []
    if signals:
        latest_signal = max(signals, key=lambda item: item.timestamp)
        top_terms = latest_signal.top_terms_delta or latest_signal.diff.get(
            "top_terms_delta", []
        )
        drift_deltas = [
            {"term": item["term"], "delta": item["delta"]}
            for item in top_terms
            if "term" in item and "delta" in item
        ]

    return ExplainResponse(
        company_id=company_id,
        intent_type=intent.intent_type,
        confidence=intent.confidence,
        readiness_score=intent.readiness_score,
        alert_eligible=bool(intent.alert_eligible),
        alert_reason=intent.alert_reason,
        rule_hits=intent.rule_hits_json or [],
        drift_deltas=drift_deltas,
        source_snippets=source_snippets,
        created_at=intent.created_at,
    )
