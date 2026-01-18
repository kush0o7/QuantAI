from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.utils.hashing import hash_string
from data.storage.db import ApiKey, RateLimit, SessionLocal
from data.storage.repositories import api_keys_repo


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allow_paths: Iterable[str] | None = None) -> None:
        super().__init__(app)
        self.allow_paths = set(allow_paths or [])

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _is_allowed_request(request, self.allow_paths):
            return await call_next(request)

        api_key_value = request.headers.get("X-API-Key")
        if not api_key_value:
            return JSONResponse({"detail": "Missing API key"}, status_code=401)

        key_hash = hash_string(api_key_value)
        with SessionLocal() as session:
            api_key = api_keys_repo.get_api_key_by_hash(session, key_hash)
            if not api_key:
                return JSONResponse({"detail": "Invalid API key"}, status_code=401)
            tenant_id = _extract_tenant_id(path)
            if tenant_id is not None and api_key.tenant_id != tenant_id:
                return JSONResponse({"detail": "API key not authorized"}, status_code=403)
            if not _check_rate_limit(session, api_key):
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
            request.state.api_key_id = api_key.id
            request.state.tenant_id = api_key.tenant_id
            api_key.last_used_at = datetime.now(timezone.utc)
            session.commit()

        return await call_next(request)


def _is_allowed_request(request: Request, allow_paths: set[str]) -> bool:
    path = request.url.path
    if path in allow_paths:
        return True
    if path.startswith("/static"):
        return True
    if path == "/tenants" and request.method in {"GET", "POST"}:
        return True
    if path.startswith("/tenants/") and path.endswith("/api-keys") and request.method == "POST":
        return True
    return False


def _extract_tenant_id(path: str) -> int | None:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "tenants" and parts[1].isdigit():
        return int(parts[1])
    return None


def _check_rate_limit(session, api_key: ApiKey) -> bool:
    limit = api_key.rate_limit_per_min or 60
    window_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rate_limit = (
        session.query(RateLimit)
        .filter(RateLimit.api_key_id == api_key.id)
        .filter(RateLimit.window_start == window_start)
        .first()
    )
    if not rate_limit:
        rate_limit = RateLimit(api_key_id=api_key.id, window_start=window_start, count=1)
        session.add(rate_limit)
        session.commit()
        return True
    if rate_limit.count >= limit:
        return False
    rate_limit.count += 1
    session.commit()
    return True
