from __future__ import annotations

from typing import Iterable
import math
import re

from core.utils.text import keyword_scores, normalize_text
from data.storage.db import IntentHypothesis, SignalEvent


IPO_PREP_RULES = [
    {
        "name": "Exec_Finance_Hire",
        "patterns": [r"\b(CFO|Chief Financial Officer|VP Finance|Head of Finance|Controller)\b"],
        "weight": 0.18,
        "signal_types": {"job_post"},
        "snippet_template": 'Senior finance leadership hire: "{match}"',
    },
    {
        "name": "IR_Hiring",
        "patterns": [r"\b(Investor Relations|IR Manager|IR Director)\b"],
        "weight": 0.14,
        "signal_types": {"job_post"},
        "snippet_template": 'Investor Relations role posted: "{match}"',
    },
    {
        "name": "SOX_Compliance",
        "patterns": [r"\b(SOX|Sarbanes[- ]Oxley|internal controls)\b"],
        "weight": 0.16,
        "signal_types": {"job_post", "sec_filing"},
        "snippet_template": 'SOX/internal controls signal: "{match}"',
    },
    {
        "name": "Public_Company_Reporting",
        "patterns": [r"\b(10-K|10-Q|Form S-1|Form S-3|SEC reporting)\b"],
        "weight": 0.12,
        "signal_types": {"sec_filing"},
        "snippet_template": 'Public reporting reference: "{match}"',
    },
    {
        "name": "Audit_Committee",
        "patterns": [r"\b(Audit Committee|independent director)\b"],
        "weight": 0.08,
        "signal_types": {"sec_filing"},
        "snippet_template": 'Governance prep: "{match}"',
    },
    {
        "name": "Legal_Securities",
        "patterns": [r"\b(securities counsel|capital markets|public company|IPO counsel)\b"],
        "weight": 0.10,
        "signal_types": {"job_post"},
        "snippet_template": 'Legal securities role: "{match}"',
    },
    {
        "name": "Revenue_Recognition",
        "patterns": [r"\b(ASC 606|revenue recognition)\b"],
        "weight": 0.06,
        "signal_types": {"sec_filing"},
        "snippet_template": 'Revenue recognition signal: "{match}"',
    },
    {
        "name": "FPandA_Scale",
        "patterns": [r"\b(FP&A|Financial Planning & Analysis|Strategic Finance)\b"],
        "weight": 0.08,
        "signal_types": {"job_post"},
        "snippet_template": 'Strategic finance scaling: "{match}"',
    },
    {
        "name": "Audit_Firm",
        "patterns": [r"\b(Big Four|KPMG|Deloitte|PwC|EY)\b"],
        "weight": 0.05,
        "signal_types": {"sec_filing"},
        "snippet_template": 'Big Four audit mention: "{match}"',
    },
    {
        "name": "Public_Company_Systems",
        "patterns": [r"\b(SOX audit|GRC|risk management|compliance systems)\b"],
        "weight": 0.06,
        "signal_types": {"job_post"},
        "snippet_template": 'Compliance systems buildout: "{match}"',
    },
    {
        "name": "IR_Tools",
        "patterns": [r"\b(roadshow|investor deck|earnings call)\b"],
        "weight": 0.05,
        "signal_types": {"sec_filing"},
        "snippet_template": 'IR communication prep: "{match}"',
    },
    {
        "name": "Equity_Admin",
        "patterns": [r"\b(equity administration|stock administration|cap table)\b"],
        "weight": 0.04,
        "signal_types": {"job_post"},
        "snippet_template": 'Equity administration role: "{match}"',
    },
]

_RULE_PATTERNS = [
    {
        **rule,
        "compiled": [re.compile(pattern, re.IGNORECASE) for pattern in rule["patterns"]],
    }
    for rule in IPO_PREP_RULES
]

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
    rule_hits = _apply_rules(signal)
    rule_weight = sum(hit["weight"] for hit in rule_hits)
    drift_score = getattr(signal, "drift_score", None)
    if drift_score is None:
        drift_score = (signal.diff or {}).get("drift_score", 0.0)
    role_bucket_delta = getattr(signal, "role_bucket_delta", None)
    if role_bucket_delta is None:
        role_bucket_delta = (signal.diff or {}).get("role_bucket_delta", {})
    role_delta_value = max(role_bucket_delta.values(), default=0.0)

    readiness_score = _readiness_score(rule_weight, drift_score, role_delta_value)
    if readiness_score < 55 and not rule_hits:
        return None

    confidence = _confidence_score(readiness_score, len(rule_hits), drift_score)
    explanation = _build_explanation(rule_hits, readiness_score)
    explanations = [
        {
            "text": explanation,
            "readiness_score": readiness_score,
            "drift_score": drift_score,
            "role_bucket_delta": role_delta_value,
            "rule_weight": rule_weight,
            "rule_hits": len(rule_hits),
        }
    ]
    return IntentHypothesis(
        company_id=signal.company_id,
        intent_type="IPO_PREP",
        confidence=confidence,
        readiness_score=readiness_score,
        created_at=signal.timestamp,
        evidence=[_evidence(signal, [hit["rule_name"] for hit in rule_hits])],
        rule_hits_json=rule_hits,
        explanations_json=explanations,
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
        created_at=signal.timestamp,
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
        created_at=signal.timestamp,
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
        created_at=signal.timestamp,
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
        created_at=signal.timestamp,
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
        created_at=signal.timestamp,
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


def _apply_rules(signal: SignalEvent) -> list[dict]:
    signal_type = getattr(signal, "signal_type", None) or "job_post"
    text = signal.raw_text or ""
    hits: list[dict] = []
    for rule in _RULE_PATTERNS:
        if signal_type not in rule["signal_types"]:
            continue
        match = _first_match(rule["compiled"], text)
        if not match:
            continue
        snippet = _extract_snippet(text, match)
        hits.append(
            {
                "rule_name": rule["name"],
                "weight": rule["weight"],
                "signal_type": signal_type,
                "match": match,
                "snippet": rule["snippet_template"].format(match=match),
                "source_snippet": snippet,
            }
        )
    return hits


def _first_match(patterns: list[re.Pattern], text: str) -> str | None:
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            return found.group(0)
    return None


def _extract_snippet(text: str, match: str, window: int = 120) -> str:
    idx = text.lower().find(match.lower())
    if idx == -1:
        return text[:200]
    start = max(0, idx - window)
    end = min(len(text), idx + len(match) + window)
    return text[start:end]


def _readiness_score(rule_weight: float, drift_score: float, role_bucket_delta: float) -> float:
    score = rule_weight + 0.6 * drift_score + 0.4 * role_bucket_delta
    return round(100.0 * (1.0 / (1.0 + math.exp(-score))), 2)


def _confidence_score(readiness_score: float, rule_hits: int, drift_score: float) -> float:
    base = readiness_score / 100.0
    if rule_hits:
        base = min(1.0, base + 0.1)
    else:
        base = min(base, 0.6)
    if drift_score < 0.2:
        base = min(base, 0.5)
    return round(base, 3)


def _build_explanation(rule_hits: list[dict], readiness_score: float) -> str:
    if not rule_hits:
        return f"IPO readiness score {readiness_score:.0f} driven by recent signal drift."
    top_rules = ", ".join(hit["rule_name"] for hit in rule_hits[:3])
    return f"IPO readiness score {readiness_score:.0f} with rule hits: {top_rules}."
