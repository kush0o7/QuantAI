from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from data.storage.db import AuditLog, SessionLocal


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)

        api_key_id = getattr(request.state, "api_key_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        with SessionLocal() as session:
            session.add(
                AuditLog(
                    api_key_id=api_key_id,
                    tenant_id=tenant_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        return response
