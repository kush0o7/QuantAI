from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from core.config import get_settings
from data.storage.db import SignalEvent

settings = get_settings()


def get_signal_by_hash(
    session: Session, tenant_id: int, company_id: int, event_hash: str
) -> SignalEvent | None:
    return session.execute(
        select(SignalEvent)
        .where(SignalEvent.tenant_id == tenant_id)
        .where(SignalEvent.company_id == company_id)
        .where(SignalEvent.event_hash == event_hash)
    ).scalars().first()


def insert_signal(session: Session, signal: SignalEvent) -> SignalEvent | None:
    existing = get_signal_by_hash(
        session, signal.tenant_id, signal.company_id, signal.event_hash
    )
    if existing:
        return None
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def list_recent_signals(
    session: Session, tenant_id: int, company_id: int, limit: int = 50
) -> list[SignalEvent]:
    return list(
        session.execute(
            select(SignalEvent)
            .where(SignalEvent.tenant_id == tenant_id)
            .where(SignalEvent.company_id == company_id)
            .order_by(desc(SignalEvent.timestamp))
            .limit(limit)
        ).scalars()
    )


def list_baseline_signals(session: Session, tenant_id: int, company_id: int) -> list[SignalEvent]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.baseline_window_days)
    return list(
        session.execute(
            select(SignalEvent)
            .where(SignalEvent.tenant_id == tenant_id)
            .where(SignalEvent.company_id == company_id)
            .where(SignalEvent.timestamp >= cutoff)
            .order_by(desc(SignalEvent.timestamp))
        ).scalars()
    )


def list_signals_since(
    session: Session, tenant_id: int, company_id: int, since: datetime
) -> list[SignalEvent]:
    return list(
        session.execute(
            select(SignalEvent)
            .where(SignalEvent.tenant_id == tenant_id)
            .where(SignalEvent.company_id == company_id)
            .where(SignalEvent.timestamp >= since)
            .order_by(desc(SignalEvent.timestamp))
        ).scalars()
    )
