from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from data.storage.db import Company, OutcomeEvent, SessionLocal, Tenant
from data.storage.repositories import company_repo, outcomes_repo, tenant_repo


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> None:
    data_path = Path(__file__).resolve().parents[1] / "data" / "backtest" / "companies.csv"
    if not data_path.exists():
        raise SystemExit(f"Missing backtest file: {data_path}")

    with SessionLocal() as session:
        tenant = tenant_repo.get_tenant_by_name(session, "Backtest")
        if not tenant:
            tenant = tenant_repo.create_tenant(session, "Backtest")

        with data_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                name = row.get("company_name", "").strip()
                domain = row.get("domain", "").strip() or None
                s1_date = parse_date(row.get("s1_date", "").strip())
                if not name:
                    continue

                company = _get_or_create_company(session, tenant.id, name, domain)
                if not s1_date:
                    continue
                if _outcome_exists(session, tenant.id, company.id, s1_date):
                    continue
                outcomes_repo.create_outcome(
                    session,
                    OutcomeEvent(
                        tenant_id=tenant.id,
                        company_id=company.id,
                        outcome_type="IPO",
                        timestamp=s1_date,
                        source="sec_seed",
                        details={"s1_date": s1_date.date().isoformat()},
                    ),
                )


def _get_or_create_company(
    session, tenant_id: int, name: str, domain: str | None
) -> Company:
    for company in company_repo.list_companies(session, tenant_id):
        if company.name == name:
            return company
    return company_repo.create_company(session, tenant_id, name, domain)


def _outcome_exists(session, tenant_id: int, company_id: int, timestamp: datetime) -> bool:
    outcomes = outcomes_repo.list_outcomes(session, tenant_id, company_id, limit=50)
    for outcome in outcomes:
        if outcome.outcome_type == "IPO" and outcome.timestamp.date() == timestamp.date():
            return True
    return False


if __name__ == "__main__":
    main()
