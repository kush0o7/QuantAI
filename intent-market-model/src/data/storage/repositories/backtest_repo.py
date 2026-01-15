from __future__ import annotations

from datetime import datetime
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from data.storage.db import IntentBacktestResult


def insert_results(session: Session, results: list[IntentBacktestResult]) -> list[IntentBacktestResult]:
    session.add_all(results)
    session.commit()
    for result in results:
        session.refresh(result)
    return results


def list_latest_run_results(
    session: Session, tenant_id: int, company_id: int
) -> list[IntentBacktestResult]:
    latest_run = session.execute(
        select(IntentBacktestResult.run_at)
        .where(IntentBacktestResult.tenant_id == tenant_id)
        .where(IntentBacktestResult.company_id == company_id)
        .order_by(desc(IntentBacktestResult.run_at))
        .limit(1)
    ).scalar()
    if not latest_run:
        return []
    return list(
        session.execute(
            select(IntentBacktestResult)
            .where(IntentBacktestResult.tenant_id == tenant_id)
            .where(IntentBacktestResult.company_id == company_id)
            .where(IntentBacktestResult.run_at == latest_run)
        ).scalars()
    )
