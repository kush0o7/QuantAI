from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.schemas.tenant import TenantCreate, TenantRead
from core.utils.hashing import hash_string
from data.storage.db import get_session
from data.storage.db import ApiKey
from data.storage.repositories import api_keys_repo, tenant_repo

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


@router.post("/tenants/{tenant_id}/api-keys", response_model=ApiKeyCreated)
def create_api_key(
    tenant_id: int, payload: ApiKeyCreate, session: Session = Depends(get_session)
):
    tenant = tenant_repo.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    raw_key = secrets.token_urlsafe(32)
    api_key = ApiKey(
        tenant_id=tenant_id,
        name=payload.name,
        key_hash=hash_string(raw_key),
        rate_limit_per_min=payload.rate_limit_per_min or 60,
    )
    api_key = api_keys_repo.create_api_key(session, api_key)
    return ApiKeyCreated(
        id=api_key.id,
        tenant_id=api_key.tenant_id,
        name=api_key.name,
        key=raw_key,
        rate_limit_per_min=api_key.rate_limit_per_min,
        created_at=api_key.created_at,
    )


@router.get("/tenants/{tenant_id}/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(tenant_id: int, session: Session = Depends(get_session)):
    tenant = tenant_repo.get_tenant(session, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return list(
        session.execute(
            select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at)
        )
        .scalars()
        .all()
    )
