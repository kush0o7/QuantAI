from __future__ import annotations

from agents.base import AgentBase
from data.storage.db import IntentHypothesis


class DecisionTranslatorAgent(AgentBase):
    name = "decision_translator"

    def translate(self, intents: list[IntentHypothesis]) -> dict[str, object]:
        investor_summary = _investor_summary(intents)

        risk = _jobseeker_risk(intents)
        jobseeker_summary = f"Stability risk: {risk}."
        return {
            "investor_summary": investor_summary,
            "jobseeker_summary": jobseeker_summary,
        }


def _investor_summary(intents: list[IntentHypothesis]) -> list[str]:
    if not intents:
        return ["No recent intent hypotheses."]
    aggregated = _aggregate_intents(intents)
    summary = []
    for intent_type, intent in aggregated.items():
        summary.append(f"{intent_type} ({intent.confidence:.2f}): {intent.explanation}")
    return summary


def _jobseeker_risk(intents: list[IntentHypothesis]) -> str:
    risk_score = 0
    for intent in intents:
        if intent.intent_type in {"COST_PRESSURE", "SUNSETTING_PRODUCTS"}:
            risk_score += 2
        if intent.intent_type == "IPO_PREP":
            risk_score += 1
    if risk_score >= 3:
        return "high"
    if risk_score == 2:
        return "medium"
    return "low"


def _aggregate_intents(intents: list[IntentHypothesis]) -> dict[str, IntentHypothesis]:
    aggregated: dict[str, IntentHypothesis] = {}
    for intent in intents:
        existing = aggregated.get(intent.intent_type)
        if not existing or intent.confidence > existing.confidence:
            aggregated[intent.intent_type] = intent
    return aggregated
