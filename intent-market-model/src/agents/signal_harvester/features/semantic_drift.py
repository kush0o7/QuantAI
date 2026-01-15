from __future__ import annotations

from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from core.config import get_settings
from core.utils.text import KEYWORDS, keyword_scores, extract_tech_tags
from data.storage.vector_store import cosine_similarity, average_embedding

settings = get_settings()

_VECTOR = HashingVectorizer(
    n_features=settings.embedding_dim,
    alternate_sign=False,
    norm=None,
)


def embed_text(text: str) -> list[float]:
    vector = _VECTOR.transform([text]).toarray()[0]
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


def compute_drift(
    text: str,
    baseline_embeddings: list[list[float]],
    baseline_keyword_scores: dict[str, int],
    baseline_tech_tags: set[str],
) -> dict:
    embedding = embed_text(text)
    baseline_embedding = average_embedding(baseline_embeddings)
    similarity = 0.0
    if baseline_embedding:
        similarity = cosine_similarity(embedding, baseline_embedding)

    keyword_shift = {}
    current_scores = keyword_scores(text, KEYWORDS)
    for key, current_value in current_scores.items():
        keyword_shift[key] = current_value - baseline_keyword_scores.get(key, 0)

    current_tags = set(extract_tech_tags(text))
    added_tags = sorted(current_tags - baseline_tech_tags)
    removed_tags = sorted(baseline_tech_tags - current_tags)

    diff = {
        "embedding_similarity": similarity,
        "keyword_shift": keyword_shift,
        "tech_stack_added": added_tags,
        "tech_stack_removed": removed_tags,
    }
    return diff, embedding


def aggregate_baseline(signals: Iterable[dict]) -> tuple[list[list[float]], dict[str, int], set[str]]:
    embeddings: list[list[float]] = []
    keyword_totals: dict[str, int] = {}
    tech_tags: set[str] = set()

    for signal in signals:
        embedding = signal.get("embedding")
        if embedding:
            embeddings.append(embedding)
        for key, value in signal.get("diff", {}).get("keyword_shift", {}).items():
            keyword_totals[key] = keyword_totals.get(key, 0) + value
        for tag in signal.get("structured_fields", {}).get("tech_tags", []):
            tech_tags.add(tag)

    return embeddings, keyword_totals, tech_tags
