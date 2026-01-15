from __future__ import annotations

from typing import Any

from core.utils.text import normalize_text
from core.utils.time import parse_datetime


def normalize_filing(filing: dict[str, Any]) -> dict[str, Any]:
    parts = [
        filing.get("title", ""),
        filing.get("section", ""),
        filing.get("body", ""),
    ]
    raw_text = normalize_text(" ".join(part for part in parts if part))
    structured_fields = {
        "filing_type": filing.get("filing_type"),
        "section": filing.get("section"),
    }
    return {
        "timestamp": parse_datetime(filing.get("filed_at")),
        "signal_type": "sec_filing",
        "raw_text": raw_text,
        "raw_text_uri": filing.get("url"),
        "structured_fields": structured_fields,
    }
