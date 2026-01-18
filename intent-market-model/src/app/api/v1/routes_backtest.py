from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import csv
from pathlib import Path
from statistics import median

from app.schemas.backtest import (
    BacktestKpiReport,
    BacktestPortfolioReport,
    BacktestReport,
    BacktestReportRow,
    BacktestReportSummary,
    BacktestRunRead,
)
from app.services.backtest_service import build_report, compute_kpis, run_backtest
from data.storage.db import get_session
from data.storage.repositories import backtest_repo, company_repo

router = APIRouter()


@router.post("/tenants/{tenant_id}/companies/{company_id}/backtest/run", response_model=BacktestRunRead)
def run_backtest_endpoint(
    tenant_id: int,
    company_id: int,
    lookback_days: int = Query(default=365, ge=30, le=1095),
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


@router.get("/tenants/{tenant_id}/companies/{company_id}/backtest/kpis", response_model=BacktestKpiReport)
def backtest_kpis(
    tenant_id: int,
    company_id: int,
    session: Session = Depends(get_session),
):
    company = company_repo.get_company(session, tenant_id, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    kpis = compute_kpis(session, tenant_id, company_id)
    return BacktestKpiReport(company_id=company_id, intent_type="IPO_PREP", kpis=kpis)


@router.get("/tenants/{tenant_id}/backtest/ipo_report", response_model=BacktestPortfolioReport)
def backtest_portfolio_report(tenant_id: int):
    report_path = Path(__file__).resolve().parents[4] / "data" / "backtest" / "report.csv"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Backtest report not found")
    rows: list[BacktestReportRow] = []
    precision: list[float] = []
    lead_times: list[float] = []
    with report_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            precision_at_k = float(row["precision_at_k"]) if row["precision_at_k"] else None
            median_lead_time = (
                float(row["median_lead_time_months"]) if row["median_lead_time_months"] else None
            )
            false_positives = int(row["false_positives"]) if row["false_positives"] else None
            rows.append(
                BacktestReportRow(
                    company_name=row["company_name"],
                    domain=row["domain"],
                    s1_date=row["s1_date"],
                    precision_at_k=precision_at_k,
                    median_lead_time_months=median_lead_time,
                    false_positives=false_positives,
                    status=row.get("status", "ok"),
                )
            )
            if precision_at_k is not None:
                precision.append(precision_at_k)
            if median_lead_time is not None:
                lead_times.append(median_lead_time)
    summary = BacktestReportSummary(
        companies=len(rows),
        precision_at_k_avg=round(sum(precision) / len(precision), 3) if precision else None,
        median_lead_time_months=round(median(lead_times), 2) if lead_times else None,
    )
    return BacktestPortfolioReport(tenant_id=tenant_id, summary=summary, rows=rows)
