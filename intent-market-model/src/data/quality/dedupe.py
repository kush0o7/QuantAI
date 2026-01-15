from typing import Any

from core.utils.hashing import stable_hash


def compute_signal_hash(payload: dict[str, Any]) -> str:
    return stable_hash(payload)
