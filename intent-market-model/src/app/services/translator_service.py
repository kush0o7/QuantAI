from __future__ import annotations

from agents.decision_translator.agent import DecisionTranslatorAgent
from data.storage.db import IntentHypothesis


class TranslatorService:
    def __init__(self) -> None:
        self.translator = DecisionTranslatorAgent()

    def summarize(self, intents: list[IntentHypothesis]) -> dict[str, object]:
        return self.translator.translate(intents)
