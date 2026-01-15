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
