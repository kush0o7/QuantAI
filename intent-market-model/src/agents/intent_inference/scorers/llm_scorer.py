from __future__ import annotations

from typing import Iterable

from data.storage.db import IntentHypothesis, SignalEvent


def score(signals: Iterable[SignalEvent]) -> list[IntentHypothesis]:
    _ = signals
    return []
