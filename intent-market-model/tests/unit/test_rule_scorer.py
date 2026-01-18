from datetime import datetime, timezone
from types import SimpleNamespace

from agents.intent_inference.scorers import rule_scorer


def test_rule_scorer_detects_ipo_prep(monkeypatch):
    monkeypatch.setattr(
        rule_scorer,
        "IntentHypothesis",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    signal = SimpleNamespace(
        id=1,
        company_id=1,
        signal_type="job_post",
        raw_text="Senior Director of Investor Relations and SOX compliance lead",
        structured_fields={"role_bucket": "security", "employment_type": "full-time"},
        drift_score=0.3,
        role_bucket_delta={"security": 0.5},
        timestamp=datetime.now(timezone.utc),
    )
    intents = rule_scorer.score([signal])
    ipo = next(intent for intent in intents if intent.intent_type == "IPO_PREP")
    assert ipo.readiness_score is not None
    assert ipo.rule_hits_json
