from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from agents.orchestrator import Orchestrator
from core.config import get_settings
from data.storage.db import get_session
from data.storage.repositories import company_repo

router = APIRouter()


@router.post("/tenants/{tenant_id}/pipeline/run")
def run_pipeline(
    tenant_id: int,
    source: str = Query(default="mock"),
    session: Session = Depends(get_session),
):
    companies = company_repo.list_companies(session, tenant_id)
    orchestrator = Orchestrator(session)
    results = orchestrator.run(companies, source=source)
    return {"processed": len(results), "inserted": results}


@router.get("/pipeline/scheduler")
def scheduler_status():
    settings = get_settings()
    return {
        "enabled": settings.enable_scheduler,
        "interval_hours": settings.scheduler_interval_hours,
        "source": settings.scheduler_source,
    }
