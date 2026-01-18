from datetime import datetime

from core.utils.hashing import stable_hash


def compute_signal_hash(
    company_id: int, source: str, raw_text: str, timestamp: datetime
) -> str:
    payload = {
        "company_id": company_id,
        "source": source,
        "raw_text": raw_text,
        "event_date": timestamp.date().isoformat(),
    }
    return stable_hash(payload)
