from __future__ import annotations

from core.config import get_settings
from data.storage.db import IntentHypothesis, SignalEvent
from agents.intent_inference.scorers import rule_scorer, llm_scorer

settings = get_settings()


def fuse(signals: list[SignalEvent]) -> list[IntentHypothesis]:
    intents = rule_scorer.score(signals)
    if settings.enable_llm_scorer:
        intents.extend(llm_scorer.score(signals))
    return intents
