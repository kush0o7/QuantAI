from __future__ import annotations

from sqlalchemy.orm import Session

from agents.base import AgentBase
from agents.signal_harvester.features.semantic_drift import compute_drift
from data.ingestion.fetcher import fetch_posts
from data.ingestion.normalizer import normalize_post
from data.ingestion.filings_normalizer import normalize_filing
from data.connectors.sec_filings import fetch_filings
from data.quality.dedupe import compute_signal_hash
from data.storage.db import Company, SignalEvent
from data.storage.repositories import signals_repo


class SignalHarvesterAgent(AgentBase):
    name = "signal_harvester"

    def __init__(self, session: Session) -> None:
        self.session = session

    def harvest(self, company: Company, source: str) -> int:
        raw_items, normalizer = _resolve_source(company, source)
        if not raw_items:
            return 0

        baseline_signals = signals_repo.list_baseline_signals(
            self.session, company.tenant_id, company.id
        )
        baseline_texts: list[str] = []
        baseline_role_counts: dict[str, int] = {}
        baseline_tech_tags: set[str] = set()
        for signal in baseline_signals:
            baseline_texts.append(signal.raw_text)
            role_bucket = signal.structured_fields.get("role_bucket")
            if role_bucket:
                baseline_role_counts[role_bucket] = baseline_role_counts.get(role_bucket, 0) + 1
            baseline_tech_tags.update(signal.structured_fields.get("tech_tags", []))

        inserted = 0
        for item in raw_items:
            normalized = normalizer(item)
            event_hash = compute_signal_hash(
                company.id, source, normalized["raw_text"], normalized["timestamp"]
            )
            if signals_repo.get_signal_by_hash(
                self.session, company.tenant_id, company.id, event_hash
            ):
                continue

            diff, tokens = compute_drift(
                normalized["raw_text"],
                normalized["signal_type"],
                normalized["structured_fields"],
                baseline_texts,
                baseline_role_counts,
                baseline_tech_tags,
            )

            signal = SignalEvent(
                tenant_id=company.tenant_id,
                company_id=company.id,
                source=source,
                timestamp=normalized["timestamp"],
                signal_type=normalized["signal_type"],
                raw_text=normalized["raw_text"],
                snippet=normalized["raw_text"][:240],
                raw_text_uri=normalized.get("raw_text_uri"),
                structured_fields=normalized["structured_fields"],
                diff=diff,
                vectorizer_version=diff["vectorizer_version"],
                tokens=tokens,
                drift_score=diff["drift_score"],
                top_terms_delta=diff["top_terms_delta"],
                role_bucket_delta=diff["role_bucket_delta"],
                tech_tag_delta=diff["tech_tag_delta"],
                event_hash=event_hash,
            )
            if signals_repo.insert_signal(self.session, signal):
                inserted += 1
                baseline_texts.append(signal.raw_text)
                role_bucket = signal.structured_fields.get("role_bucket")
                if role_bucket:
                    baseline_role_counts[role_bucket] = (
                        baseline_role_counts.get(role_bucket, 0) + 1
                    )
                baseline_tech_tags.update(signal.structured_fields.get("tech_tags", []))
        return inserted


def _resolve_source(company: Company, source: str):
    company_key = company.domain or company.name
    if source == "greenhouse" and company.greenhouse_board:
        company_key = company.greenhouse_board
    if source in {"sec_mock", "sec"}:
        return fetch_filings(company_key), normalize_filing
    return fetch_posts(company_key, source), normalize_post
