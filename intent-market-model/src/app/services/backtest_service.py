from __future__ import annotations

from datetime import datetime, timedelta, timezone

from data.storage.db import IntentBacktestResult, IntentHypothesis
from data.storage.repositories import backtest_repo, intents_repo, outcomes_repo

OUTCOME_INTENT_MAP = {
    "IPO": ["IPO_PREP"],
    "LAYOFF": ["COST_PRESSURE", "SUNSETTING_PRODUCTS"],
    "FUNDING": ["PRODUCT_EXPANSION", "PLATFORM_PIVOT"],
}


def run_backtest(session, tenant_id: int, company_id: int, lookback_days: int) -> list[IntentBacktestResult]:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    outcomes = outcomes_repo.list_outcomes_since(session, tenant_id, company_id, since)
    intents = intents_repo.list_latest_intents(session, tenant_id, company_id, limit=500)

    intents_by_type: dict[str, list[IntentHypothesis]] = {}
    for intent in intents:
        intents_by_type.setdefault(intent.intent_type, []).append(intent)

    run_at = datetime.now(timezone.utc)
    results: list[IntentBacktestResult] = []
    for outcome in outcomes:
        mapped = OUTCOME_INTENT_MAP.get(outcome.outcome_type, [])
        best_intent = _find_best_intent(intents_by_type, mapped, outcome.timestamp)
        if best_intent:
            lag_days = (outcome.timestamp - best_intent.created_at).days
            results.append(
                IntentBacktestResult(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    outcome_id=outcome.id,
                    outcome_type=outcome.outcome_type,
                    intent_id=best_intent.id,
                    intent_type=best_intent.intent_type,
                    outcome_timestamp=outcome.timestamp,
                    intent_timestamp=best_intent.created_at,
                    lag_days=float(lag_days),
                    matched=True,
                    run_at=run_at,
                )
            )
        else:
            results.append(
                IntentBacktestResult(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    outcome_id=outcome.id,
                    outcome_type=outcome.outcome_type,
                    intent_id=None,
                    intent_type=None,
                    outcome_timestamp=outcome.timestamp,
                    intent_timestamp=None,
                    lag_days=None,
                    matched=False,
                    run_at=run_at,
                )
            )

    return backtest_repo.insert_results(session, results)


def build_report(results: list[IntentBacktestResult]) -> tuple[datetime | None, list[dict]]:
    if not results:
        return None, []
    run_at = results[0].run_at
    metrics: dict[str, dict] = {}
    for result in results:
        metric = metrics.setdefault(
            result.outcome_type,
            {"outcomes": 0, "matched": 0, "lag_sum": 0.0, "lag_count": 0},
        )
        metric["outcomes"] += 1
        if result.matched and result.lag_days is not None:
            metric["matched"] += 1
            metric["lag_sum"] += result.lag_days
            metric["lag_count"] += 1

    report = []
    for outcome_type, metric in metrics.items():
        avg_lag = None
        if metric["lag_count"]:
            avg_lag = metric["lag_sum"] / metric["lag_count"]
        match_rate = metric["matched"] / metric["outcomes"] if metric["outcomes"] else 0.0
        report.append(
            {
                "outcome_type": outcome_type,
                "outcomes": metric["outcomes"],
                "matched": metric["matched"],
                "match_rate": match_rate,
                "avg_lag_days": avg_lag,
            }
        )
    return run_at, report


def _find_best_intent(
    intents_by_type: dict[str, list[IntentHypothesis]],
    intent_types: list[str],
    outcome_time: datetime,
) -> IntentHypothesis | None:
    candidates: list[IntentHypothesis] = []
    for intent_type in intent_types:
        for intent in intents_by_type.get(intent_type, []):
            if intent.created_at <= outcome_time:
                candidates.append(intent)
    if not candidates:
        return None
    return max(candidates, key=lambda intent: intent.created_at)


def compute_kpis(
    session,
    tenant_id: int,
    company_id: int,
    intent_type: str = "IPO_PREP",
    k: int = 20,
    window_days: int = 365,
    readiness_threshold: float = 70.0,
) -> dict:
    outcomes = outcomes_repo.list_outcomes(session, tenant_id, company_id, limit=500)
    ipo_outcomes = [o for o in outcomes if o.outcome_type == "IPO"]
    if ipo_outcomes:
        min_outcome = min(o.timestamp for o in ipo_outcomes)
        max_outcome = max(o.timestamp for o in ipo_outcomes)
        window_start = min_outcome - timedelta(days=window_days)
        window_end = max_outcome
    else:
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
        window_end = datetime.now(timezone.utc)

    intents = [
        intent
        for intent in intents_repo.list_company_intents(session, tenant_id, company_id)
        if intent.intent_type == intent_type
        and intent.created_at >= window_start
        and intent.created_at <= window_end
    ]

    def intent_score(item: IntentHypothesis) -> float:
        return item.readiness_score if item.readiness_score is not None else item.confidence

    intents_sorted = sorted(intents, key=intent_score, reverse=True)
    top_k = intents_sorted[:k]
    def has_ipo_within_window(intent: IntentHypothesis) -> bool:
        for outcome in ipo_outcomes:
            delta = outcome.timestamp - intent.created_at
            if 0 <= delta.days <= window_days:
                return True
        return False

    hits = sum(1 for intent in top_k if has_ipo_within_window(intent))
    precision_at_k = hits / k if k else 0.0

    lead_time_months = None
    first_trigger = None
    for intent in sorted(intents, key=lambda item: item.created_at):
        score = intent.readiness_score or 0.0
        if score >= readiness_threshold:
            first_trigger = intent.created_at
            break
    if first_trigger and ipo_outcomes:
        ipo_after = [o.timestamp for o in ipo_outcomes if o.timestamp >= first_trigger]
        if ipo_after:
            first_ipo = min(ipo_after)
            lead_days = (first_ipo - first_trigger).days
            lead_time_months = round(lead_days / 30.0, 2)

    false_positives = 0
    for intent in intents:
        score = intent.readiness_score or 0.0
        if score >= readiness_threshold and not has_ipo_within_window(intent):
            false_positives += 1

    return {
        "precision_at_k": precision_at_k,
        "k": k,
        "median_lead_time_months": lead_time_months,
        "false_positives": false_positives,
    }
