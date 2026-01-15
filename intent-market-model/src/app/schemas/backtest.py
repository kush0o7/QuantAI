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
