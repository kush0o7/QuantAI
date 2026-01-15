from __future__ import annotations

from sqlalchemy.orm import Session

from agents.base import AgentBase
from agents.signal_harvester.features.semantic_drift import compute_drift
from core.utils.text import keyword_scores, extract_tech_tags
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
        raw_items, normalizer = _resolve_source(company.domain or company.name, source)
        if not raw_items:
            return 0

        baseline_signals = signals_repo.list_baseline_signals(
            self.session, company.tenant_id, company.id
        )
        baseline_embeddings = [s.embedding for s in baseline_signals if s.embedding]
        baseline_keyword_scores = {}
        baseline_tech_tags = set()
        baseline_count = 0
        for signal in baseline_signals:
            baseline_keyword_scores = _merge_keyword_scores(
                baseline_keyword_scores, keyword_scores(signal.raw_text)
            )
            baseline_tech_tags.update(extract_tech_tags(signal.raw_text))
            baseline_count += 1
        if baseline_count:
            baseline_keyword_scores = {
                key: int(value / baseline_count) for key, value in baseline_keyword_scores.items()
            }

        inserted = 0
        for item in raw_items:
            normalized = normalizer(item)
            content_hash = compute_signal_hash(normalized)
            if signals_repo.get_signal_by_hash(
                self.session, company.tenant_id, company.id, content_hash
            ):
                continue

            diff, embedding = compute_drift(
                normalized["raw_text"],
                baseline_embeddings,
                baseline_keyword_scores,
                baseline_tech_tags,
            )

            signal = SignalEvent(
                tenant_id=company.tenant_id,
                company_id=company.id,
                source=source,
                timestamp=normalized["timestamp"],
                signal_type=normalized["signal_type"],
                raw_text=normalized["raw_text"],
                raw_text_uri=normalized.get("raw_text_uri"),
                structured_fields=normalized["structured_fields"],
                diff=diff,
                content_hash=content_hash,
                embedding=embedding,
            )
            if signals_repo.insert_signal(self.session, signal):
                inserted += 1
                baseline_embeddings.append(embedding)
                baseline_keyword_scores = _merge_keyword_scores(
                    baseline_keyword_scores, keyword_scores(signal.raw_text)
                )
                baseline_tech_tags.update(signal.structured_fields.get("tech_tags", []))
        return inserted


def _resolve_source(company_key: str, source: str):
    if source in {"sec_mock", "sec"}:
        return fetch_filings(company_key), normalize_filing
    return fetch_posts(company_key, source), normalize_post


def _merge_keyword_scores(base: dict[str, int], incoming: dict[str, int]) -> dict[str, int]:
    merged = dict(base)
    for key, value in incoming.items():
        merged[key] = merged.get(key, 0) + value
    return merged
