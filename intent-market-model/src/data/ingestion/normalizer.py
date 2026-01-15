from __future__ import annotations

from typing import Any

from core.utils.text import extract_tech_tags, infer_role_bucket
from core.utils.time import parse_datetime
from data.ingestion.parser import build_raw_text


def normalize_post(post: dict[str, Any]) -> dict[str, Any]:
    raw_text = build_raw_text(post)
    title = post.get("title", "")
    structured_fields = {
        "title": title,
        "team": post.get("team"),
        "location": post.get("location"),
        "employment_type": post.get("employment_type"),
        "seniority": post.get("seniority"),
        "role_bucket": infer_role_bucket(title),
        "tech_tags": extract_tech_tags(raw_text),
    }
    return {
        "timestamp": parse_datetime(post.get("posted_at")),
        "signal_type": "job_post",
        "raw_text": raw_text,
        "raw_text_uri": post.get("url"),
        "structured_fields": structured_fields,
    }
