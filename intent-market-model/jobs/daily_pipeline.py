from __future__ import annotations

from typing import Iterable

from core.config import get_settings
from core.logger import setup_logging
from data.storage.db import SessionLocal
from data.storage.repositories import company_repo, tenant_repo
from agents.orchestrator import Orchestrator


def _parse_watchlist(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def run() -> dict[int, int]:
    settings = get_settings()
    setup_logging()
    with SessionLocal() as session:
        results: dict[int, int] = {}
        watchlist = _parse_watchlist(settings.watchlist_companies)
        orchestrator = Orchestrator(session)
        for tenant in tenant_repo.list_tenants(session):
            companies = company_repo.list_companies(session, tenant.id)
            if watchlist:
                companies = [
                    c for c in companies if c.domain in watchlist or c.name in watchlist
                ]
            results.update(orchestrator.run(companies))
        return results


if __name__ == "__main__":
    results = run()
    for company_id, inserted in results.items():
        print(f"{company_id}: inserted {inserted}")
