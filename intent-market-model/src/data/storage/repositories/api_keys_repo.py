from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.storage.db import ApiKey


def create_api_key(session: Session, api_key: ApiKey) -> ApiKey:
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return api_key


def get_api_key_by_hash(session: Session, key_hash: str) -> ApiKey | None:
    return session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash)).scalars().first()
