from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from data.storage.db import ResponseCache


def get_cached_response(session: Session, cache_key: str) -> dict | None:
    now = datetime.now(timezone.utc)
    record = (
        session.execute(
            select(ResponseCache)
            .where(ResponseCache.cache_key == cache_key)
            .where(ResponseCache.expires_at > now)
        )
        .scalars()
        .first()
    )
    if not record:
        return None
    return record.payload


def set_cached_response(session: Session, cache_key: str, payload: dict, ttl_seconds: int = 600) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    record = (
        session.execute(select(ResponseCache).where(ResponseCache.cache_key == cache_key))
        .scalars()
        .first()
    )
    if record:
        record.payload = payload
        record.expires_at = expires_at
    else:
        record = ResponseCache(cache_key=cache_key, payload=payload, expires_at=expires_at)
        session.add(record)
    session.commit()


def invalidate_cache_prefix(session: Session, prefix: str) -> None:
    session.execute(delete(ResponseCache).where(ResponseCache.cache_key.like(f"{prefix}%")))
    session.commit()
