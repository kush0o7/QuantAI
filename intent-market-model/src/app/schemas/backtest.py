from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BacktestRunRead(BaseModel):
    results_count: int
    run_at: datetime | None


class BacktestMetric(BaseModel):
    outcome_type: str
    outcomes: int
    matched: int
    match_rate: float
    avg_lag_days: float | None


class BacktestReport(BaseModel):
    company_id: int
    run_at: datetime | None
    metrics: list[BacktestMetric]


class BacktestKpi(BaseModel):
    precision_at_k: float
    k: int
    median_lead_time_months: float | None
    false_positives: int


class BacktestKpiReport(BaseModel):
    company_id: int
    intent_type: str
    kpis: BacktestKpi


class BacktestReportRow(BaseModel):
    company_name: str
    domain: str
    s1_date: str
    precision_at_k: float | None
    median_lead_time_months: float | None
    false_positives: int | None
    status: str


class BacktestReportSummary(BaseModel):
    companies: int
    precision_at_k_avg: float | None
    median_lead_time_months: float | None


class BacktestPortfolioReport(BaseModel):
    tenant_id: int
    summary: BacktestReportSummary
    rows: list[BacktestReportRow]
