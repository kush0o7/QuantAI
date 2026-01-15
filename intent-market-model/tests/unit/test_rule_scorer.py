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
        raw_text="compliance governance audit security risk controls",
        structured_fields={"role_bucket": "security", "employment_type": "full-time"},
    )
    intents = rule_scorer.score([signal])
    assert any(intent.intent_type == "IPO_PREP" for intent in intents)
