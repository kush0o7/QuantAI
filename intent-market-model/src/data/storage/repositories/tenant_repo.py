from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.storage.db import Tenant


def create_tenant(session: Session, name: str) -> Tenant:
    tenant = Tenant(name=name)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def list_tenants(session: Session) -> list[Tenant]:
    return list(session.execute(select(Tenant).order_by(Tenant.id)).scalars())


def get_tenant(session: Session, tenant_id: int) -> Tenant | None:
    return session.get(Tenant, tenant_id)
