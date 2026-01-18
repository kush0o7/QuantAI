from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from agents.base import AgentBase
from agents.intent_inference.fusion import fuse
from data.storage.db import IntentHypothesis, SignalEvent
from data.storage.repositories import intents_repo, signals_repo

_READINESS_THRESHOLD = 70.0
_PERSISTENCE_DAYS = 60
_SOURCE_WINDOW_DAYS = 30


class IntentInferenceAgent(AgentBase):
    name = "intent_inference"

    def __init__(self, session: Session) -> None:
        self.session = session

    def infer(self, signals: list[SignalEvent]) -> list[IntentHypothesis]:
        if not signals:
            return []
        tenant_id = signals[0].tenant_id
        existing_pairs, existing_signal_ids = _load_existing_intents(
            self.session, tenant_id, signals[0].company_id
        )
        fresh_signals = [
            signal for signal in signals if signal.id and signal.id not in existing_signal_ids
        ]
        intents = fuse(fresh_signals)
        if not intents:
            return []
        for intent in intents:
            intent.tenant_id = tenant_id
            if intent.intent_type == "IPO_PREP":
                _apply_trust_layer(self.session, tenant_id, intent)
        intents = _dedupe_intents(intents, existing_pairs)
        if not intents:
            return []
        return intents_repo.insert_intents(self.session, intents)


def _load_existing_intents(
    session: Session, tenant_id: int, company_id: int
) -> tuple[set[tuple[str, int]], set[int]]:
    existing_pairs: set[tuple[str, int]] = set()
    existing_signal_ids: set[int] = set()
    for intent in intents_repo.list_company_intents(session, tenant_id, company_id):
        for evidence in intent.evidence or []:
            signal_id = evidence.get("signal_event_id")
            if signal_id is None:
                continue
            existing_signal_ids.add(signal_id)
            existing_pairs.add((intent.intent_type, signal_id))
    return existing_pairs, existing_signal_ids


def _dedupe_intents(
    intents: list[IntentHypothesis], existing_pairs: set[tuple[str, int]]
) -> list[IntentHypothesis]:
    seen: set[tuple[str, int]] = set(existing_pairs)
    deduped: list[IntentHypothesis] = []
    for intent in intents:
        signal_id = None
        if intent.evidence:
            signal_id = intent.evidence[0].get("signal_event_id")
        if signal_id is None:
            deduped.append(intent)
            continue
        key = (intent.intent_type, int(signal_id))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(intent)
    return deduped


def _apply_trust_layer(session: Session, tenant_id: int, intent: IntentHypothesis) -> None:
    readiness = intent.readiness_score or 0.0
    if readiness < _READINESS_THRESHOLD:
        intent.alert_eligible = False
        intent.alert_reason = f"Readiness below {_READINESS_THRESHOLD:.0f} threshold."
        _append_trust_explanation(intent, 0, False, False)
        return

    reference_time = intent.created_at or datetime.now(timezone.utc)
    since_persistence = reference_time - timedelta(days=_PERSISTENCE_DAYS)
    since_sources = reference_time - timedelta(days=_SOURCE_WINDOW_DAYS)

    recent_intents = intents_repo.list_intents_since(
        session, tenant_id, intent.company_id, since_persistence, intent_type="IPO_PREP"
    )
    persisted = any(
        prior.readiness_score is not None and prior.readiness_score >= _READINESS_THRESHOLD
        for prior in recent_intents
    )

    recent_signals = signals_repo.list_signals_since(
        session, tenant_id, intent.company_id, since_sources
    )
    source_count = len({signal.source for signal in recent_signals})
    multi_source = source_count >= 2

    if persisted or multi_source:
        intent.alert_eligible = True
        if persisted and multi_source:
            intent.alert_reason = "Readiness persisted and confirmed across sources."
        elif persisted:
            intent.alert_reason = "Readiness persisted across periods."
        else:
            intent.alert_reason = "Readiness confirmed across multiple sources."
    else:
        intent.alert_eligible = False
        intent.alert_reason = "Readiness high but not persistent or multi-source yet."

    _append_trust_explanation(intent, source_count, persisted, multi_source)


def _append_trust_explanation(
    intent: IntentHypothesis, source_count: int, persisted: bool, multi_source: bool
) -> None:
    explanations = intent.explanations_json or []
    explanations.append(
        {
            "alert_eligible": intent.alert_eligible,
            "alert_reason": intent.alert_reason,
            "persistence_window_days": _PERSISTENCE_DAYS,
            "source_window_days": _SOURCE_WINDOW_DAYS,
            "source_count": source_count,
            "persisted": persisted,
            "multi_source": multi_source,
        }
    )
    intent.explanations_json = explanations
