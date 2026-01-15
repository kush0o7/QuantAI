from __future__ import annotations

from sqlalchemy.orm import Session

from agents.base import AgentBase
from agents.intent_inference.fusion import fuse
from data.storage.db import IntentHypothesis, SignalEvent
from data.storage.repositories import intents_repo


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
