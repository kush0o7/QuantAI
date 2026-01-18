from __future__ import annotations

from typing import Iterable
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from core.utils.text import KEYWORDS, ROLE_HINTS, TECH_STACK_TAGS, normalize_text, extract_tech_tags
from data.storage.vector_store import cosine_similarity

VECTORIZER_VERSION = "tfidf-v1"
_TOKEN_RE = re.compile(r"[a-z][a-z0-9_+\-\.]{1,}")


def tokenize_text(text: str) -> list[str]:
    normalized = normalize_text(text)
    return _TOKEN_RE.findall(normalized)


def _build_vocab() -> list[str]:
    vocab: set[str] = set()
    for terms in KEYWORDS.values():
        for term in terms:
            vocab.update(tokenize_text(term))
    for tag in TECH_STACK_TAGS.keys():
        vocab.add(tag)
    for hints in ROLE_HINTS.values():
        for hint in hints:
            vocab.update(tokenize_text(hint))
    return sorted(vocab)


_VOCAB = _build_vocab()


def compute_drift(
    text: str,
    signal_type: str,
    structured_fields: dict,
    baseline_texts: list[str],
    baseline_role_counts: dict[str, int],
    baseline_tech_tags: set[str],
) -> tuple[dict, list[str]]:
    tokens = tokenize_text(text)

    drift_score = 0.0
    top_terms_delta: list[dict[str, float | str]] = []
    if baseline_texts:
        corpus = baseline_texts + [text]
        vectorizer = TfidfVectorizer(
            vocabulary=_VOCAB,
            tokenizer=tokenize_text,
            lowercase=False,
            token_pattern=None,
        )
        tfidf = vectorizer.fit_transform(corpus)
        current_vec = tfidf[-1].toarray()[0]
        baseline_vec = tfidf[:-1].mean(axis=0).A1
        similarity = cosine_similarity(current_vec.tolist(), baseline_vec.tolist())
        drift_score = max(0.0, 1.0 - similarity)

        delta = current_vec - baseline_vec
        top_idx = np.argsort(delta)[::-1]
        terms = vectorizer.get_feature_names_out()
        for idx in top_idx[:10]:
            if delta[idx] <= 0:
                break
            top_terms_delta.append({"term": terms[idx], "delta": float(delta[idx])})

    role_bucket_delta: dict[str, float] = {}
    if signal_type == "job_post":
        bucket = structured_fields.get("role_bucket", "other")
        baseline_total = sum(baseline_role_counts.values())
        baseline_share = (
            baseline_role_counts.get(bucket, 0) / baseline_total if baseline_total else 0.0
        )
        role_bucket_delta = {bucket: 1.0 - baseline_share}

    current_tags = set(extract_tech_tags(text))
    tech_tag_delta = {
        "added": sorted(current_tags - baseline_tech_tags),
        "removed": sorted(baseline_tech_tags - current_tags),
    }

    diff = {
        "vectorizer_version": VECTORIZER_VERSION,
        "drift_score": drift_score,
        "top_terms_delta": top_terms_delta,
        "role_bucket_delta": role_bucket_delta,
        "tech_tag_delta": tech_tag_delta,
    }
    return diff, tokens


def aggregate_baseline(signals: Iterable[dict]) -> tuple[list[str], dict[str, int], set[str]]:
    texts: list[str] = []
    role_counts: dict[str, int] = {}
    tech_tags: set[str] = set()

    for signal in signals:
        raw_text = signal.get("raw_text")
        if raw_text:
            texts.append(raw_text)
        role = signal.get("structured_fields", {}).get("role_bucket")
        if role:
            role_counts[role] = role_counts.get(role, 0) + 1
        for tag in signal.get("structured_fields", {}).get("tech_tags", []):
            tech_tags.add(tag)

    return texts, role_counts, tech_tags
