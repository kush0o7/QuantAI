from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.tenant import TenantCreate, TenantRead
from data.storage.db import get_session
from data.storage.repositories import tenant_repo

router = APIRouter()


@router.post("/tenants", response_model=TenantRead)
def create_tenant(payload: TenantCreate, session: Session = Depends(get_session)):
    tenant = tenant_repo.create_tenant(session, payload.name)
    return tenant


@router.get("/tenants", response_model=list[TenantRead])
def list_tenants(session: Session = Depends(get_session)):
    return tenant_repo.list_tenants(session)


@router.get("/tenants/{tenant_id}", response_model=TenantRead)
def get_tenant(tenant_id: int, session: Session = Depends(get_session)):
    tenant = tenant_repo.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
