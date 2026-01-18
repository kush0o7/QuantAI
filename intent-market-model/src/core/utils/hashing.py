import hashlib
import json
from datetime import datetime
from typing import Any


def stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=_default)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
