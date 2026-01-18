from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agents.intent_inference.agent import IntentInferenceAgent
from data.quality.dedupe import compute_signal_hash
from data.storage.db import Company, IntentHypothesis, SignalEvent, SessionLocal
from data.storage.repositories import company_repo, signals_repo, tenant_repo


IPO_RULE_TEXT = (
    "CFO Investor Relations SOX Sarbanes-Oxley internal controls 10-K 10-Q "
    "Audit Committee securities counsel capital markets FP&A revenue recognition "
    "Big Four Deloitte PwC EY KPMG equity administration roadshow investor deck"
)

BASE_TEXT = (
    "Hiring for backend infrastructure and product growth roles to scale platform systems."
)


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    companies_path = root / "data" / "backtest" / "companies.csv"
    snapshots_path = root / "data" / "backtest" / "hiring_snapshots.csv"
    if not companies_path.exists():
        raise SystemExit(f"Missing companies list: {companies_path}")

    snapshot_rows: list[dict[str, str]] = []

    with SessionLocal() as session:
        tenant = tenant_repo.get_tenant_by_name(session, "Backtest")
        if not tenant:
            tenant = tenant_repo.create_tenant(session, "Backtest")

        with companies_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                name = row.get("company_name", "").strip()
                domain = row.get("domain", "").strip() or None
                s1_date = parse_date(row.get("s1_date", "").strip())
                if not name:
                    continue
                company = _get_or_create_company(session, tenant.id, name, domain)
                _seed_company_signals(session, company, s1_date, snapshot_rows)
                _run_inference(session, company)

    _write_snapshots(snapshots_path, snapshot_rows)


def _get_or_create_company(
    session, tenant_id: int, name: str, domain: str | None
) -> Company:
    for company in company_repo.list_companies(session, tenant_id):
        if company.name == name:
            return company
    return company_repo.create_company(session, tenant_id, name, domain)


def _seed_company_signals(
    session, company: Company, s1_date: datetime | None, snapshot_rows: list[dict[str, str]]
) -> None:
    session.query(IntentHypothesis).filter(
        IntentHypothesis.tenant_id == company.tenant_id,
        IntentHypothesis.company_id == company.id,
    ).delete(synchronize_session=False)
    session.query(SignalEvent).filter(
        SignalEvent.tenant_id == company.tenant_id,
        SignalEvent.company_id == company.id,
        SignalEvent.source == "backtest_seed",
    ).delete(synchronize_session=False)
    session.commit()
    if s1_date:
        anchor = s1_date - timedelta(days=15)
    else:
        anchor = datetime.now(timezone.utc)

    for idx in range(12):
        timestamp = anchor - timedelta(days=(11 - idx) * 30)
        is_ipo_window = idx >= 8
        raw_text = BASE_TEXT
        if is_ipo_window:
            raw_text = f"{BASE_TEXT} {IPO_RULE_TEXT}"
        structured_fields = {
            "title": "Finance Director" if is_ipo_window else "Software Engineer",
            "role_bucket": "finance" if is_ipo_window else "infra",
        }
        event_hash = compute_signal_hash(company.id, "backtest_seed", raw_text, timestamp)
        signal = SignalEvent(
            tenant_id=company.tenant_id,
            company_id=company.id,
            source="backtest_seed",
            timestamp=timestamp,
            signal_type="job_post",
            raw_text=raw_text,
            raw_text_uri=None,
            snippet=raw_text[:240],
            structured_fields=structured_fields,
            diff={},
            vectorizer_version=None,
            tokens=[],
            drift_score=None,
            top_terms_delta=[],
            role_bucket_delta={},
            tech_tag_delta={},
            event_hash=event_hash,
            embedding=None,
        )
        signals_repo.insert_signal(session, signal)
        snapshot_rows.append(
            {
                "company_name": company.name,
                "domain": company.domain or "",
                "timestamp": timestamp.isoformat(),
                "source": "backtest_seed",
                "signal_type": "job_post",
                "raw_text": raw_text,
            }
        )


def _run_inference(session, company: Company) -> None:
    signals = signals_repo.list_recent_signals(session, company.tenant_id, company.id, limit=200)
    if not signals:
        return
    agent = IntentInferenceAgent(session)
    agent.infer(signals)


def _write_snapshots(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["company_name", "domain", "timestamp", "source", "signal_type", "raw_text"],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
