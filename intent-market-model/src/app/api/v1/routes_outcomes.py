from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.outcome import OutcomeCreate, OutcomeRead
from data.storage.db import OutcomeEvent, get_session
from data.storage.repositories import company_repo, outcomes_repo

router = APIRouter()


@router.post("/tenants/{tenant_id}/companies/{company_id}/outcomes", response_model=OutcomeRead)
def create_outcome(
    tenant_id: int,
    company_id: int,
    payload: OutcomeCreate,
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    outcome = OutcomeEvent(
        tenant_id=tenant_id,
        company_id=company_id,
        outcome_type=payload.outcome_type,
        timestamp=payload.timestamp,
        source=payload.source,
        details=payload.details or {},
    )
    return outcomes_repo.create_outcome(session, outcome)


@router.get("/tenants/{tenant_id}/companies/{company_id}/outcomes", response_model=list[OutcomeRead])
def list_outcomes(
    tenant_id: int,
    company_id: int,
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return outcomes_repo.list_outcomes(session, tenant_id, company_id)
