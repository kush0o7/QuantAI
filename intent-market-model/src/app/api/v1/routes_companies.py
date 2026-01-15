from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agents.signal_harvester.agent import SignalHarvesterAgent
from agents.intent_inference.agent import IntentInferenceAgent
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.signal_event import SignalEventRead
from data.storage.db import get_session
from data.storage.repositories import company_repo, signals_repo

router = APIRouter()


@router.post("/", response_model=CompanyRead)
def create_company(
    tenant_id: int,
    payload: CompanyCreate,
    session: Session = Depends(get_session),
):
    company = company_repo.create_company(session, tenant_id, payload.name, payload.domain)
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
    return {"inserted": inserted, "intents_created": intents_created}


@router.get("/{company_id}/signals/recent", response_model=list[SignalEventRead])
def recent_signals(tenant_id: int, company_id: int, session: Session = Depends(get_session)):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return signals_repo.list_recent_signals(session, tenant_id, company_id)
