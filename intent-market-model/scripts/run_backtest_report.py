from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from app.services.backtest_service import compute_kpis
from data.storage.db import SessionLocal
from data.storage.repositories import company_repo, tenant_repo


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    companies_path = root / "data" / "backtest" / "companies.csv"
    report_path = root / "data" / "backtest" / "report.csv"
    if not companies_path.exists():
        raise SystemExit(f"Missing companies list: {companies_path}")

    rows = []
    with SessionLocal() as session:
        tenant = tenant_repo.get_tenant_by_name(session, "Backtest")
        if not tenant:
            raise SystemExit("Backtest tenant missing. Run seed_backtest_outcomes.py first.")

        companies = company_repo.list_companies(session, tenant.id)

        with companies_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for entry in reader:
                name = entry.get("company_name", "").strip()
                domain = entry.get("domain", "").strip()
                s1_date = entry.get("s1_date", "").strip()
                company = _match_company(companies, name, domain)
                if not company:
                    rows.append(
                        {
                            "company_name": name,
                            "domain": domain,
                            "s1_date": s1_date,
                            "precision_at_k": "",
                            "median_lead_time_months": "",
                            "false_positives": "",
                            "status": "missing_company",
                        }
                    )
                    continue
                kpis = compute_kpis(session, tenant.id, company.id)
                rows.append(
                    {
                        "company_name": name,
                        "domain": domain,
                        "s1_date": s1_date,
                        "precision_at_k": f"{kpis['precision_at_k']:.3f}",
                        "median_lead_time_months": kpis["median_lead_time_months"] or "",
                        "false_positives": kpis["false_positives"],
                        "status": "ok",
                    }
                )

    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "company_name",
                "domain",
                "s1_date",
                "precision_at_k",
                "median_lead_time_months",
                "false_positives",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = _summarize(rows)
    print(f"Report written to {report_path}")
    print(summary)


def _match_company(companies, name: str, domain: str | None):
    for company in companies:
        if company.name == name:
            return company
        if domain and company.domain == domain:
            return company
    return None


def _summarize(rows: list[dict]) -> dict:
    precision = []
    lead_times = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        if row.get("precision_at_k"):
            precision.append(float(row["precision_at_k"]))
        if row.get("median_lead_time_months"):
            lead_times.append(float(row["median_lead_time_months"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companies": len(rows),
        "precision_at_k_avg": round(sum(precision) / len(precision), 3) if precision else None,
        "median_lead_time_months": round(median(lead_times), 2) if lead_times else None,
    }


if __name__ == "__main__":
    main()
