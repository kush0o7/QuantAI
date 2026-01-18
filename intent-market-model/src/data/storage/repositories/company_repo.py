from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.storage.db import Company


def create_company(
    session: Session,
    tenant_id: int,
    name: str,
    domain: str | None,
    greenhouse_board: str | None = None,
) -> Company:
    company = Company(
        tenant_id=tenant_id, name=name, domain=domain, greenhouse_board=greenhouse_board
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def list_companies(session: Session, tenant_id: int) -> list[Company]:
    return list(
        session.execute(
            select(Company)
            .where(Company.tenant_id == tenant_id)
            .order_by(Company.id)
        ).scalars()
    )


def get_company(session: Session, tenant_id: int, company_id: int) -> Company | None:
    return session.execute(
        select(Company)
        .where(Company.tenant_id == tenant_id)
        .where(Company.id == company_id)
    ).scalars().first()
