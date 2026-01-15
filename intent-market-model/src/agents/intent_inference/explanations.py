from __future__ import annotations


def normalize_explanation(text: str) -> str:
    return " ".join(text.strip().split())
