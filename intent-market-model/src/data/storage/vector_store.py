from __future__ import annotations

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_vec = np.array(a)
    b_vec = np.array(b)
    denom = (np.linalg.norm(a_vec) * np.linalg.norm(b_vec))
    if denom == 0:
        return 0.0
    return float(np.dot(a_vec, b_vec) / denom)


def average_embedding(embeddings: list[list[float]]) -> list[float] | None:
    if not embeddings:
        return None
    stacked = np.array(embeddings)
    return stacked.mean(axis=0).tolist()
