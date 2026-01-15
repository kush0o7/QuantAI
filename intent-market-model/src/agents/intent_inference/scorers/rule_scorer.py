from __future__ import annotations

from typing import Iterable

from core.utils.text import keyword_scores, normalize_text
from data.storage.db import IntentHypothesis, SignalEvent


IPO_TERMS = ["compliance", "governance", "audit", "sox"]
SECURITY_TERMS = ["security", "risk", "privacy"]
PLATFORM_TERMS = ["platform", "infrastructure", "infra"]
SUNSET_TERMS = ["sunset", "deprecate", "migrate off"]
COST_TERMS = ["optimize", "efficiency", "cost", "contract", "contractor"]
PRODUCT_TERMS = ["product", "growth", "expansion"]


def score(signals: Iterable[SignalEvent]) -> list[IntentHypothesis]:
    intents: list[IntentHypothesis] = []
    for signal in signals:
        text = normalize_text(signal.raw_text)
        scores = keyword_scores(text)
        structured = signal.structured_fields or {}
        role_bucket = structured.get("role_bucket")
        employment_type = (structured.get("employment_type") or "").lower()

        intent = _ipo_prep(signal, text, scores)
        if intent:
            intents.append(intent)

        intent = _security_ramp(signal, text, scores)
        if intent:
            intents.append(intent)

        intent = _platform_pivot(signal, text, role_bucket)
        if intent:
            intents.append(intent)

        intent = _cost_pressure(signal, text, scores, employment_type)
        if intent:
            intents.append(intent)

        intent = _sunsetting(signal, text)
        if intent:
            intents.append(intent)

        intent = _product_expansion(signal, text, scores, role_bucket)
        if intent:
            intents.append(intent)

    return intents


def _ipo_prep(signal: SignalEvent, text: str, scores: dict[str, int]) -> IntentHypothesis | None:
    compliance_hits = _count_terms(text, IPO_TERMS)
    security_hits = _count_terms(text, SECURITY_TERMS)
    if compliance_hits + security_hits < 2:
        return None
    confidence = min(0.85, 0.6 + 0.05 * (compliance_hits + security_hits))
    explanation = (
        "The posting emphasizes governance and compliance work alongside security risk management. "
        "These are typical preparations for tighter reporting controls and external scrutiny."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="IPO_PREP",
        confidence=confidence,
        evidence=[_evidence(signal, ["compliance", "security"])],
        explanation=explanation,
    )


def _security_ramp(signal: SignalEvent, text: str, scores: dict[str, int]) -> IntentHypothesis | None:
    security_hits = _count_terms(text, SECURITY_TERMS)
    compliance_hits = _count_terms(text, IPO_TERMS)
    if security_hits + compliance_hits < 2:
        return None
    confidence = min(0.8, 0.55 + 0.05 * (security_hits + compliance_hits))
    explanation = (
        "Security and compliance language increases in this role description. "
        "The company appears to be expanding its risk and governance capacity."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="SECURITY_COMPLIANCE_RAMP",
        confidence=confidence,
        evidence=[_evidence(signal, ["security", "compliance"])],
        explanation=explanation,
    )


def _platform_pivot(signal: SignalEvent, text: str, role_bucket: str | None) -> IntentHypothesis | None:
    if role_bucket not in {"infra", "ml"}:
        return None
    if not _has_any(text, PLATFORM_TERMS):
        return None
    if "product" in text:
        return None
    confidence = 0.65 if role_bucket == "ml" else 0.6
    explanation = (
        "The hiring focus is on infrastructure and internal platforms rather than outward product roles. "
        "This suggests a pivot toward building shared platform capabilities."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="PLATFORM_PIVOT",
        confidence=confidence,
        evidence=[_evidence(signal, ["platform", role_bucket or "infra"])],
        explanation=explanation,
    )


def _cost_pressure(
    signal: SignalEvent, text: str, scores: dict[str, int], employment_type: str
) -> IntentHypothesis | None:
    cost_hits = _count_terms(text, COST_TERMS)
    if cost_hits == 0 and "contract" not in employment_type:
        return None
    confidence = min(0.75, 0.55 + 0.05 * cost_hits)
    explanation = (
        "The role language highlights efficiency and flexible staffing. "
        "That pattern aligns with cost pressure and headcount caution."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="COST_PRESSURE",
        confidence=confidence,
        evidence=[_evidence(signal, ["efficiency", "contract"])],
        explanation=explanation,
    )


def _sunsetting(signal: SignalEvent, text: str) -> IntentHypothesis | None:
    if not _has_any(text, SUNSET_TERMS):
        return None
    confidence = 0.7
    explanation = (
        "Terms like sunset or deprecate appear in the job description. "
        "This implies active work to retire or migrate products or systems."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="SUNSETTING_PRODUCTS",
        confidence=confidence,
        evidence=[_evidence(signal, ["sunset", "deprecate"])],
        explanation=explanation,
    )


def _product_expansion(
    signal: SignalEvent, text: str, scores: dict[str, int], role_bucket: str | None
) -> IntentHypothesis | None:
    if role_bucket != "product":
        return None
    if scores.get("scale", 0) == 0 and not _has_any(text, PRODUCT_TERMS):
        return None
    confidence = 0.6
    explanation = (
        "Product-oriented hiring paired with growth language suggests new feature or market expansion. "
        "The company may be preparing to scale customer-facing capabilities."
    )
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="PRODUCT_EXPANSION",
        confidence=confidence,
        evidence=[_evidence(signal, ["product", "scale"])],
        explanation=explanation,
    )


def _evidence(signal: SignalEvent, triggers: list[str]) -> dict:
    snippet = signal.raw_text[:200]
    return {
        "signal_event_id": signal.id,
        "snippet": snippet,
        "triggers": triggers,
    }


def _count_terms(text: str, terms: list[str]) -> int:
    return sum(text.count(term) for term in terms)


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)
