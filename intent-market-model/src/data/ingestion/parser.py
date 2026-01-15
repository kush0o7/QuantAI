from __future__ import annotations

from typing import Any

from core.utils.text import normalize_text


def build_raw_text(post: dict[str, Any]) -> str:
    parts = [
        post.get("title", ""),
        post.get("team", ""),
        post.get("location", ""),
        post.get("description", ""),
        post.get("requirements", ""),
    ]
    return normalize_text(" ".join(p for p in parts if p))
