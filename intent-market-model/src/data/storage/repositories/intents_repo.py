from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from data.storage.db import IntentHypothesis


def insert_intents(session: Session, intents: list[IntentHypothesis]) -> list[IntentHypothesis]:
    session.add_all(intents)
    session.commit()
    for intent in intents:
        session.refresh(intent)
    return intents


def list_latest_intents(
    session: Session,
    tenant_id: int,
    company_id: int,
    limit: int = 10,
    intent_types: list[str] | None = None,
    min_confidence: float | None = None,
) -> list[IntentHypothesis]:
    query = select(IntentHypothesis).where(
        IntentHypothesis.tenant_id == tenant_id,
        IntentHypothesis.company_id == company_id,
    )
    if intent_types:
        query = query.where(IntentHypothesis.intent_type.in_(intent_types))
    if min_confidence is not None:
        query = query.where(IntentHypothesis.confidence >= min_confidence)
    query = query.order_by(desc(IntentHypothesis.created_at)).limit(limit)
    return list(session.execute(query).scalars())


def list_company_intents(session: Session, tenant_id: int, company_id: int) -> list[IntentHypothesis]:
    return list(
        session.execute(
            select(IntentHypothesis).where(
                IntentHypothesis.tenant_id == tenant_id,
                IntentHypothesis.company_id == company_id,
            )
        ).scalars()
    )


def list_intents_since(
    session: Session, tenant_id: int, company_id: int, since
) -> list[IntentHypothesis]:
    return list(
        session.execute(
            select(IntentHypothesis)
            .where(IntentHypothesis.tenant_id == tenant_id)
            .where(IntentHypothesis.company_id == company_id)
            .where(IntentHypothesis.created_at >= since)
            .order_by(IntentHypothesis.created_at)
        ).scalars()
    )
