from __future__ import annotations

from sqlalchemy.orm import Session

from agents.signal_harvester.agent import SignalHarvesterAgent
from agents.intent_inference.agent import IntentInferenceAgent
from agents.causal_memory.agent import CausalMemoryAgent
from data.storage.repositories import signals_repo
from data.storage.db import Company


class Orchestrator:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.harvester = SignalHarvesterAgent(session)
        self.inferencer = IntentInferenceAgent(session)
        self.causal = CausalMemoryAgent()

    def run(self, companies: list[Company], source: str = "mock") -> dict[int, int]:
        results: dict[int, int] = {}
        sources = [item.strip() for item in source.split(",") if item.strip()]
        for company in companies:
            total_inserted = 0
            for src in sources:
                total_inserted += self.harvester.harvest(company, src)
            recent_signals = signals_repo.list_recent_signals(
                self.session, company.tenant_id, company.id, limit=50
            )
            intents = self.inferencer.infer(recent_signals)
            self.causal.update_memory(intents, outcomes=[])
            results[company.id] = total_inserted
        return results
