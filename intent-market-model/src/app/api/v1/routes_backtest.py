from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.backtest import BacktestReport, BacktestRunRead
from app.services.backtest_service import build_report, run_backtest
from data.storage.db import get_session
from data.storage.repositories import backtest_repo, company_repo

router = APIRouter()


@router.post("/tenants/{tenant_id}/companies/{company_id}/backtest/run", response_model=BacktestRunRead)
def run_backtest_endpoint(
    tenant_id: int,
    company_id: int,
    lookback_days: int = Query(default=365, ge=30, le=730),
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    results = run_backtest(session, tenant_id, company_id, lookback_days)
    run_at = results[0].run_at if results else None
    return BacktestRunRead(results_count=len(results), run_at=run_at)


@router.get("/tenants/{tenant_id}/companies/{company_id}/backtest/report", response_model=BacktestReport)
def backtest_report(
    tenant_id: int,
    company_id: int,
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    results = backtest_repo.list_latest_run_results(session, tenant_id, company_id)
    run_at, metrics = build_report(results)
    return BacktestReport(company_id=company_id, run_at=run_at, metrics=metrics)
