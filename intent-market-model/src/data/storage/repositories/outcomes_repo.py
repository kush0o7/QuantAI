from __future__ import annotations

from datetime import datetime
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from data.storage.db import OutcomeEvent


def create_outcome(session: Session, outcome: OutcomeEvent) -> OutcomeEvent:
    session.add(outcome)
    session.commit()
    session.refresh(outcome)
    return outcome


def list_outcomes(
    session: Session, tenant_id: int, company_id: int, limit: int = 100
) -> list[OutcomeEvent]:
    return list(
        session.execute(
            select(OutcomeEvent)
            .where(OutcomeEvent.tenant_id == tenant_id)
            .where(OutcomeEvent.company_id == company_id)
            .order_by(desc(OutcomeEvent.timestamp))
            .limit(limit)
        ).scalars()
    )


def list_outcomes_since(
    session: Session, tenant_id: int, company_id: int, since: datetime
) -> list[OutcomeEvent]:
    return list(
        session.execute(
            select(OutcomeEvent)
            .where(OutcomeEvent.tenant_id == tenant_id)
            .where(OutcomeEvent.company_id == company_id)
            .where(OutcomeEvent.timestamp >= since)
            .order_by(desc(OutcomeEvent.timestamp))
        ).scalars()
    )
