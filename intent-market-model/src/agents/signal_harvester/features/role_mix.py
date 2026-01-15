from collections import Counter

from core.utils.text import infer_role_bucket


def role_mix(posts: list[dict]) -> dict[str, int]:
    counts = Counter()
    for post in posts:
        title = post.get("structured_fields", {}).get("title", "")
        counts[infer_role_bucket(title)] += 1
    return dict(counts)
