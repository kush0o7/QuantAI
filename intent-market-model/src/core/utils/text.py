import re
from typing import Iterable


KEYWORDS = {
    "scale": ["scale", "scaling", "growth"],
    "optimize": ["optimize", "efficiency", "cost"],
    "sunset": ["sunset", "deprecate", "migrate off"],
    "compliance": ["compliance", "governance", "audit"],
    "security": ["security", "risk", "privacy"],
    "platform": ["platform", "infra", "infrastructure"],
    "ml_infra": ["ml infrastructure", "ml platform", "feature store"],
}

TECH_STACK_TAGS = {
    "aws": [r"\baws\b", r"amazon web services"],
    "gcp": [r"\bgcp\b", r"google cloud"],
    "azure": [r"\bazure\b"],
    "kubernetes": [r"kubernetes", r"\bk8s\b"],
    "terraform": [r"terraform"],
    "spark": [r"spark"],
    "kafka": [r"kafka"],
    "databricks": [r"databricks"],
    "snowflake": [r"snowflake"],
    "postgres": [r"postgres", r"postgresql"],
}

ROLE_HINTS = {
    "product": ["product", "pm"],
    "infra": ["infra", "infrastructure", "platform"],
    "security": ["security", "compliance", "risk"],
    "ml": ["ml", "machine learning"],
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def keyword_scores(text: str, keywords: dict[str, Iterable[str]] = KEYWORDS) -> dict[str, int]:
    normalized = normalize_text(text)
    scores: dict[str, int] = {}
    for label, terms in keywords.items():
        scores[label] = sum(normalized.count(term) for term in terms)
    return scores


def extract_tech_tags(text: str) -> list[str]:
    normalized = normalize_text(text)
    tags = []
    for tag, patterns in TECH_STACK_TAGS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                tags.append(tag)
                break
    return sorted(set(tags))


def infer_role_bucket(title: str) -> str:
    normalized = normalize_text(title)
    for role, hints in ROLE_HINTS.items():
        if any(hint in normalized for hint in hints):
            return role
    return "other"
